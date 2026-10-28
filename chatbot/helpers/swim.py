from datetime import timedelta

from swims.models import PublicSwimProduct
from django.utils import timezone
import pytz

from timetable.closures import closure_for, closures_between
from timetable.today import booked_swimmers, places_left

def get_available_swims():
    dublin = pytz.timezone("Europe/Dublin")
    now = timezone.now().astimezone(dublin)
    today = now.date()
    weekday = today.weekday()
    current_time = now.time()

    all_swims = PublicSwimProduct.objects.filter(available=True)

    # Today's sessions only count while they are still running.
    upcoming = [
        swim for swim in all_swims
        if swim.day_of_week != weekday or swim.end_time > current_time
    ]

    # Order by how many days ahead each session is, wrapping around the end of the
    # week. Sorting on the raw day number put Sunday last whatever day it was, so on
    # a Saturday the list ran Monday, Tuesday, ... and the cap below cut Sunday off
    # entirely — the genuinely next session was not in the list the bot was given.
    # Only Sunday and Monday came out right, being the two days from which the raw
    # numbers already ascend; Tuesday through Saturday were all wrong.
    upcoming.sort(key=lambda s: ((s.day_of_week - weekday) % 7, s.start_time))

    # Each session's actual date this week, and none on a day staff have marked
    # closed: the bot said "we're open tomorrow" on a closed bank holiday.
    closures = closures_between(today, today + timedelta(days=6))
    for swim in upcoming:
        swim.next_date = today + timedelta(days=(swim.day_of_week - weekday) % 7)
    upcoming = [s for s in upcoming if not closure_for('swim', s.next_date, closures)]
    # Places left that day, counted as the timetable counts them; num_places alone
    # is the session's size, which the bot was quoting as "places available".
    booked = booked_swimmers(today, today + timedelta(days=6))
    for swim in upcoming:
        swim.places_left = places_left(swim, swim.next_date, booked)

    return upcoming[:15]

def _when(swim):
    next_date = getattr(swim, 'next_date', None)
    if next_date is None:
        return swim.get_day_of_week_display()
    return f"{next_date:%A} {next_date.day} {next_date:%B}"


def _places(swim):
    left = getattr(swim, 'places_left', swim.num_places)
    if left is None:
        return "places available"
    return "fully booked" if left == 0 else f"{left} places left"


def format_swim_list(swims):
    def get_price_table(product):
        prices = product.price_variants.all()
        if not prices:
            return ""
        price_lines = [f"  - {pv.get_variant_display()}: €{pv.price:.2f}" for pv in prices]
        return f"\n**Prices:**\n" + "\n".join(price_lines)

    return "\n\n".join([
        f"- **{s.name}** on **{_when(s)}** from **{s.start_time.strftime('%H:%M')}** to **{s.end_time.strftime('%H:%M')}** – **{_places(s)}**\n{get_price_table(s)}"
        for s in swims
    ])
