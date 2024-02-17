import django_filters
from .models import ScoLessons

class ProductFilter(django_filters.FilterSet):
    class Meta:
        model = ScoLessons
        fields = ['category', 'day_of_week']  # Add any other filter fields as needed
