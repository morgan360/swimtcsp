// A date as YYYY-MM-DD in the visitor's own time zone. toISOString() is UTC, so
// just after midnight in Irish summer time it gave yesterday's date.
function localYmd(d) {
    return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, '0')}-${String(d.getDate()).padStart(2, '0')}`;
}

function timetableApp() {
    return {
        currentTab: 'swims',
        startDate: new Date(),
        today: localYmd(new Date()),
        events: [],
        // Per day: the closures customers should see (from the API).
        days: [],
        // The day view shows one day at a time; 0 is today.
        selectedDay: 0,
        showWeek: false,
        // Re-read every minute so "On now" and "Next" stay right on an open tab.
        now: new Date(),

        init() {
            // ?day=1 opens on tomorrow (the homepage links there once today's swims are over).
            const params = new URLSearchParams(window.location.search);
            const day = parseInt(params.get('day'), 10);
            if (day >= 0 && day < 7) this.selectedDay = day;
            // ?tab=calendar or ?tab=lessons, so other pages can link straight there.
            if (['swims', 'lessons', 'calendar'].includes(params.get('tab'))) this.currentTab = params.get('tab');
            this.recordTab(this.currentTab);
            setInterval(() => { this.now = new Date(); }, 60000);
        },

        fetchEvents() {
            const iso = localYmd(this.startDate);
            const endpoint = this.currentTab === 'swims'
                ? `/timetable/api/public/?start=${iso}`
                : `/timetable/api/week/?start=${iso}`;

            fetch(endpoint)
                .then(res => {
                    if (!res.ok) throw new Error(`Fetch failed: ${res.status}`);
                    return res.json();
                })
                .then(data => {
                    this.events = data.events || [];
                    this.days = data.days || [];
                })
                .catch(err => {
                    console.error("Timetable fetch error:", err);
                    this.events = [];
                    this.days = [];
                });
        },

        // --- Day view --------------------------------------------------------

        kind() {
            return this.currentTab === 'lessons' ? 'lesson' : 'swim';
        },

        chipLabel(index) {
            if (index === 0) return 'Today';
            if (index === 1) return 'Tomorrow';
            const d = new Date(this.startDate);
            d.setDate(d.getDate() + index);
            return d.toLocaleDateString('en-IE', {weekday: 'short'});
        },

        chipDate(index) {
            const d = new Date(this.startDate);
            d.setDate(d.getDate() + index);
            return d.toLocaleDateString('en-IE', {day: 'numeric', month: 'short'});
        },

        longDayLabel(index) {
            const d = new Date(this.startDate);
            d.setDate(d.getDate() + index);
            const name = d.toLocaleDateString('en-IE', {weekday: 'long', day: 'numeric', month: 'long'});
            return index === 0 ? `Today, ${name}` : index === 1 ? `Tomorrow, ${name}` : name;
        },

        sessionsOn(index) {
            const ymd = this.dateFor(index);
            const kind = this.kind();
            return this.events
                .filter(e => e.date === ymd && e.type === kind)
                .sort((a, b) => a.start.localeCompare(b.start) || a.title.localeCompare(b.title));
        },

        // Lessons run several levels at once, so the day view lists them by time.
        lessonBlocksOn(index) {
            const blocks = {};
            for (const e of this.sessionsOn(index)) {
                const key = `${e.start}–${e.end}`;
                (blocks[key] = blocks[key] || []).push(e);
            }
            return Object.entries(blocks);
        },

        // The plain answer at the top: open, or closed and why.
        dayStatus(index) {
            const day = this.days[index];
            const closures = day ? day.closures : [];
            const whole = closures.find(c => c.affects === 'all');
            const kind = this.kind();
            const mine = closures.find(c => c.affects === (kind === 'swim' ? 'swims' : 'lessons'));
            const what = kind === 'swim' ? 'public swims' : 'lessons';
            const d = new Date(this.startDate);
            d.setDate(d.getDate() + index);
            const when = index === 0 ? 'today' : index === 1 ? 'tomorrow'
                : 'on ' + d.toLocaleDateString('en-IE', {weekday: 'long'});
            if (whole) return {tone: 'closed', text: `Pool closed ${when}`, reason: whole.title};
            if (mine) return {tone: 'closed', text: `No ${what} ${when}`, reason: mine.title};
            const count = this.sessionsOn(index).length;
            if (!count) return {tone: 'quiet', text: `No ${what} ${when}`, reason: ''};
            if (kind === 'lesson') return {tone: 'open', text: `Lessons ${when}`, reason: ''};
            return {tone: 'open', text: `Open ${when}`, reason: `${count} public swim${count === 1 ? '' : 's'}`};
        },

        isClosedDay(index) {
            return this.dayStatus(index).tone === 'closed';
        },

        minutes(hhmm) {
            const [h, m] = hhmm.split(':').map(Number);
            return h * 60 + m;
        },

        // 'now', 'next', 'over' or '' for a session today; '' on other days.
        sessionState(event, index) {
            if (index !== 0 || event.closed) return '';
            const nowMins = this.now.getHours() * 60 + this.now.getMinutes();
            if (this.minutes(event.end) <= nowMins) return 'over';
            if (this.minutes(event.start) <= nowMins) return 'now';
            const next = this.sessionsOn(0).find(e => !e.closed && this.minutes(e.start) > nowMins);
            return next === event ? 'next' : '';
        },

        canBook(event, index) {
            return event.book_url && !event.closed && event.places_left !== 0
                && this.sessionState(event, index) !== 'over';
        },

        // Counts which tabs people use (timetable.views.tab_seen); no cookies, nothing
        // about who. Never allowed to get in the way of the page.
        recordTab(tab) {
            try {
                const form = new FormData();
                form.append('tab', tab);
                navigator.sendBeacon('/timetable/seen/', form);
            } catch (e) { /* counting is optional */ }
        },

        switchTab(tab) {
            if (tab !== this.currentTab) this.recordTab(tab);
            this.currentTab = tab;
            // The calendar is rendered by the server (timetable/year.py); nothing to fetch.
            if (tab !== 'calendar') this.fetchEvents();
        },


        dateFor(index) {
            const d = new Date(this.startDate);
            d.setDate(d.getDate() + index);
            return localYmd(d);
        },

        dayLabel(index) {
            const d = new Date(this.startDate);
            d.setDate(d.getDate() + index);
            return d.toLocaleDateString('en-IE', {weekday: 'short', day: 'numeric', month: 'short'});
        },

        formatTime(t) {
            return t?.slice(0, 5);
        },

        formatTimeRange(range) {
            const parts = range.split('–');
            return this.formatTime(parts[0]) + '–' + this.formatTime(parts[1]);
        },

        cleanTitle(title) {
            return title
                .replace(/\b(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday)\b/g, '')
                .replace(/\d{2}:\d{2}\s*(to|-)\s*\d{2}:\d{2}/g, '')
                .replace(/[-–]{1,2}/g, ' ')
                .replace(/\s+/g, ' ')
                .trim();
        },

        groupedEventsForDay(index) {
            const d = new Date(this.startDate);
            d.setDate(d.getDate() + index);
            const ymd = localYmd(d);

            const dayEvents = this.events.filter(e =>
                e.date === ymd &&
                e.type === this.currentTab.slice(0, -1) // "lessons" → "lesson", "swims" → "swim"
            );

            const grouped = {};
            for (const event of dayEvents) {
                const key = `${event.start}–${event.end}`;
                if (!grouped[key]) grouped[key] = [];
                grouped[key].push(event);
            }

            return grouped;
        },
        eventIcon(type, category) {
            if (!category) return '❓';
            const cat = category.toLowerCase();

            if (type === 'lesson') {
                if (cat.includes('improver')) return '📘';
                if (cat.includes('beginner')) return '🧒';
                if (cat.includes('advanced')) return '🥇';
                if (cat.includes('parent-baby')) return '👶';
                if (cat.includes('teen')) return '🧑‍🎓';
                return '📘'; // fallback for lessons
            }

            // Swims
            if (cat.includes('lane')) return '🏊';
            if (cat.includes('family')) return '👨‍👩‍👧';
            if (cat.includes('recovery')) return '🧍‍♂️';
            if (cat.includes('school')) return '🎒';
            if (cat.includes('masters')) return '🧓';
            if (cat.includes('oap')) return '👴';
            if (cat.includes('aerobics') || cat.includes('aqua')) return '💃';
            return '💧';
        }
    }
}
