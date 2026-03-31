from django.contrib.admin.filters import RelatedFieldListFilter


class SearchableRelatedDropdownFilter(RelatedFieldListFilter):
    """A dropdown filter with a search box to filter options."""
    template = 'django_admin_listfilter_dropdown/searchable_dropdown_filter.html'