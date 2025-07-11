from django.contrib.admin import SimpleListFilter
from schools_bookings.models import ScoTerm


class TermFilter(SimpleListFilter):
    title = 'Term Selection'
    parameter_name = 'term'

    def lookups(self, request, model_admin):
        terms = ScoTerm.objects.filter(is_active=True).order_by('-start_date')
        return [(term.id, f"{term} - {term.start_date}") for term in terms]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(term__id=self.value())
        return queryset


class DayOfWeekFilter(SimpleListFilter):
    title = 'Day of Week'
    parameter_name = 'day_of_week'

    def lookups(self, request, model_admin):
        return [(i, day) for i, day in enumerate([
            'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'
        ])]

    def queryset(self, request, queryset):
        if self.value() is not None:
            return queryset.filter(lesson__day_of_week=self.value())
        return queryset
