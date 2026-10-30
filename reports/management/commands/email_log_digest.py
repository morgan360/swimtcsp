# reports/management/commands/email_log_digest.py
"""Email the last day's production errors, with the noise taken out.

Run daily as a PythonAnywhere scheduled task. A Claude routine reads the email
from Gmail and writes the triage report, because the routine runs in the cloud
and cannot SSH in to read the logs itself. The email is sent even when there is
nothing to report, so a missing digest means the task itself has stopped.

The web error log gets ~1,000 lines a day of bot 404s, client disconnects and a
pkg_resources warning. Those are counted, not listed, so the real errors stand
out. The subject always starts with SUBJECT_PREFIX, which the routine searches on.
"""
import glob
import os
import re
from collections import Counter
from datetime import datetime, timedelta, timezone as dt_timezone

from django.conf import settings
from django.core.mail import send_mail
from django.core.management.base import BaseCommand

SUBJECT_PREFIX = '[TCSP log digest]'
WEB_LOG = '/var/log/www.tcsp.ie.error.log'
SERVER_LOG = '/var/log/www.tcsp.ie.server.log'
SCHEDULE_LOGS = '/var/log/schedule-log-*.log'
MAX_LINES = 400  # per section, so one runaway error can't swamp the email

STAMP = re.compile(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d)')
# Web error log noise: counted under these labels, never listed.
WEB_NOISE = [
    ('404 Not Found', re.compile(r'^Not Found: (\S+)')),
    ('Client disconnected (OSError: write error)', re.compile(r'^OSError: write error')),
    ('Outbound HTTP 2xx (OpenAI etc.)', re.compile(r'^HTTP Request: .* "HTTP/1\.1 2\d\d')),
    ('pkg_resources deprecation warning', re.compile(r'pkg_resources')),
]
APP_LEVEL = re.compile(r'^\S+ \S+ (ERROR|WARNING|CRITICAL) ')
SERVER_KEEP = re.compile(r'harakiri|killed|MemoryError|out of memory|segmentation|traceback|error|died', re.I)
TASK_DONE = re.compile(r'return code was (\d+)')


def read_entries(paths, since):
    """Yield (timestamp, text) for entries at or after `since`.

    A line with no timestamp (a traceback from logger.exception) belongs to the
    entry above it. `.1` files are read too, so a rotation overnight loses nothing.
    """
    for path in paths:
        for candidate in (path + '.1', path):
            if not os.path.exists(candidate):
                continue
            stamp, lines = None, []
            with open(candidate, errors='replace') as fh:
                for line in fh:
                    line = line.rstrip('\n')
                    match = STAMP.match(line)
                    if match:
                        if stamp and stamp >= since:
                            yield stamp, '\n'.join(lines)
                        stamp = datetime.strptime(match.group(1), '%Y-%m-%d %H:%M:%S')
                        lines = [line]
                    elif stamp:
                        lines.append(line)
            if stamp and stamp >= since:
                yield stamp, '\n'.join(lines)


def message_of(text):
    """The entry with its timestamp prefix removed, for grouping repeats."""
    first, _, rest = text.partition('\n')
    first = re.sub(r'^\d{4}-\d\d-\d\d \d\d:\d\d:\d\d(,\d+)?:? ?', '', first)
    return '\n'.join(filter(None, [first, rest]))


def grouped(entries):
    """Collapse identical messages to one line with a count and time range."""
    groups = {}
    for stamp, message in entries:
        first, last, count = groups.get(message, (stamp, stamp, 0))
        groups[message] = (min(first, stamp), max(last, stamp), count + 1)
    lines = []
    for message, (first, last, count) in sorted(groups.items(), key=lambda g: g[1][0]):
        when = f'{first:%H:%M}' if count == 1 else f'{count}× {first:%H:%M}–{last:%H:%M}'
        lines.append(f'[{when}] {message}')
    return lines


def capped(lines):
    text = '\n'.join(lines)
    split = text.split('\n')
    if len(split) > MAX_LINES:
        split = split[:MAX_LINES] + [f'… {len(split) - MAX_LINES} more lines cut']
    return '\n'.join(split)


def build_digest(since, web_log=WEB_LOG, server_log=SERVER_LOG,
                 app_logs=None, schedule_logs=SCHEDULE_LOGS):
    """Return (item count, body text) for everything logged since `since`."""
    if app_logs is None:
        log_base = getattr(settings, 'LOG_BASE', os.path.join(settings.BASE_DIR, 'logs'))
        app_logs = sorted(glob.glob(os.path.join(log_base, '*.log')))
    sections, items = [], 0

    noise, not_found, web = Counter(), Counter(), []
    for stamp, text in read_entries([web_log], since):
        message = message_of(text)
        for label, pattern in WEB_NOISE:
            match = pattern.search(message)
            if match:
                noise[label] += 1
                if label == '404 Not Found':
                    not_found[match.group(1)] += 1
                break
        else:
            web.append((stamp, message))
    web_lines = grouped(web)
    items += len(web_lines)
    sections.append(('Web app error log (www.tcsp.ie)', capped(web_lines) or 'Nothing.'))

    app = []
    for path in app_logs:
        name = os.path.basename(path)
        for stamp, text in read_entries([path], since):
            if APP_LEVEL.match(text):
                app.append((stamp, f'{name}: {message_of(text)}'))
    app_lines = grouped(app)
    items += len(app_lines)
    sections.append(('Application logs: WARNING and above', capped(app_lines) or 'Nothing.'))

    server, disconnects = [], 0
    for stamp, text in read_entries([server_log], since):
        if 'SIGPIPE' in text:
            disconnects += 1
        elif SERVER_KEEP.search(text):
            server.append((stamp, message_of(text)))
    server_lines = grouped(server)
    items += len(server_lines)
    sections.append(('uWSGI server log', capped(server_lines) or 'Nothing.'))

    # These are every scheduled task on the account, not only this site's.
    tasks = []
    for path in sorted(glob.glob(schedule_logs)):
        output = ''
        for stamp, text in read_entries([path], since):
            match = TASK_DONE.search(text)
            if not match:
                # "Started task" plus whatever the task printed
                output = '\n'.join(l for l in message_of(text).split('\n') if l.strip())
                continue
            line = f'{os.path.basename(path)}: {message_of(text).strip()}'
            if match.group(1) == '0':
                tasks.append(f'OK. {line}')
            else:
                tasks.append(f'FAILED. {line}\n{output}')
    items += sum(t.startswith('FAILED') for t in tasks)
    sections.append(('Scheduled tasks finished', '\n'.join(tasks) or 'None ran.'))

    counted = [f'{label}: {count}' for label, count in noise.most_common()]
    if disconnects:
        counted.append(f'uWSGI SIGPIPE (client went away): {disconnects}')
    if not_found:
        counted.append('Top 404 paths: ' + ', '.join(
            f'{path} ({count})' for path, count in not_found.most_common(10)))
    # Not an item to look at: they are blocked already and don't get an email each.
    from security.models import SecurityIncident
    scanners = SecurityIncident.objects.filter(
        kind=SecurityIncident.PROBE_BLOCKED, created__gte=since.replace(tzinfo=dt_timezone.utc)).count()
    sections.append(('Scanners blocked', f'{scanners} address(es) blocked for an hour. See Security on the Live Dashboard.'))

    sections.append(('Counted as noise, not listed', '\n'.join(counted) or 'None.'))

    body = f'Logged since {since:%Y-%m-%d %H:%M} (server time, UTC).\n'
    for title, text in sections:
        body += f'\n=== {title} ===\n{text}\n'
    return items, body


class Command(BaseCommand):
    help = "Email the last day's production errors, with the noise taken out"

    def add_arguments(self, parser):
        parser.add_argument('--to', help='Address to send the digest to')
        parser.add_argument('--hours', type=int, default=24)
        parser.add_argument('--dry-run', action='store_true', help='Print instead of sending')

    def handle(self, *args, **options):
        since = datetime.utcnow() - timedelta(hours=options['hours'])
        items, body = build_digest(since)
        subject = f'{SUBJECT_PREFIX} {datetime.utcnow():%Y-%m-%d}: {items} item(s) to look at'

        if options['dry_run'] or not options['to']:
            self.stdout.write(f'{subject}\n\n{body}')
            return
        send_mail(subject, body, settings.DEFAULT_FROM_EMAIL, [options['to']])
        self.stdout.write(self.style.SUCCESS(f'✅ Sent to {options["to"]}: {items} item(s)'))