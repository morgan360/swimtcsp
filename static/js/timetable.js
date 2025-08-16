function timetableApp() {
    return {
        currentTab: 'swims',
        startDate: new Date(),
        today: new Date().toISOString().split('T')[0],
        events: [],

        fetchEvents() {
  const iso = this.startDate.toISOString().split('T')[0];

  // ✅ Correct paths based on your Django URLs
  // ✅ Correct
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
    })
    .catch(err => {
      console.error("Timetable fetch error:", err);
      this.events = [];
    });
},


        // Inside the returned object:
        calendarInitialized: false,

        switchTab(tab) {
            this.currentTab = tab;
            if (tab === 'calendar' && !this.calendarInitialized) {
                this.loadCalendar();
                this.calendarInitialized = true;
            } else {
                this.fetchEvents();
            }
        },

        loadCalendar() {
            this.$nextTick(() => {
                const calendarEl = document.getElementById('calendar');
                if (!calendarEl) return;

                const calendar = new FullCalendar.Calendar(calendarEl, {
                    initialView: 'dayGridMonth',
                    headerToolbar: {
                        left: 'prev,next today',
                        center: 'title',
                        right: 'dayGridMonth,listYear'
                    },
                    views: {
                        listYear: {
                            buttonText: 'Year'
                        }
                    },
                    events: '/timetable/calendar/events/',
                    height: 'auto',
                    eventDisplay: 'block'
                });

                calendar.render();
            });
        },


        dateFor(index) {
            const d = new Date(this.startDate);
            d.setDate(d.getDate() + index);
            return d.toISOString().split('T')[0];
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
            const ymd = d.toISOString().split('T')[0];

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
