function timetableApp() {
    return {
        currentTab: 'lessons',
        startDate: new Date(),
        today: new Date().toISOString().split('T')[0],
        events: [],

        fetchEvents() {
            const iso = this.startDate.toISOString().split('T')[0];
            const endpoint = this.currentTab === 'swims'
                ? `/timetable/api/public/?start=${iso}`
                : `/timetable/api/week/?start=${iso}`;
            fetch(endpoint)
                .then(res => res.json())
                .then(data => {
                    this.events = data.events;
                });
        },

        switchTab(tab) {
            this.currentTab = tab;
            this.fetchEvents();
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

            const dayEvents = this.events.filter(e => e.date === ymd);
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
