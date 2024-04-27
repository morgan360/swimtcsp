from django import forms
import django_filters
from .models import ScoSchool, ScoLessons, ScoCategory  # Assuming ScoCategory is your category model

class LessonFilter(django_filters.FilterSet):
    school = django_filters.ModelChoiceFilter(
        queryset=ScoSchool.objects.filter(school_lessons__isnull=False).distinct(),
        widget=forms.Select(),
        label='School'
    )
    category = django_filters.ModelChoiceFilter(
        queryset=ScoCategory.objects.filter(scolessons__isnull=False).distinct(),  # Assuming the related_name is 'scolessons' or similar
        widget=forms.Select(),
        label='Category'
    )
    # active = django_filters.BooleanFilter(widget=forms.CheckboxInput(), label='Active')

    class Meta:
        model = ScoLessons
        fields = ['school', 'category']


