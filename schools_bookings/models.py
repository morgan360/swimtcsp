from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from schools.models import ScoLessons, ScoSchool
from users.models import Swimling
from django.utils.formats import date_format
from django.utils import timezone

# from lessons_orders.models import Order
# Because of circular references had to use string references instead: 'lessons_orders.Order'


class ScoTerm(models.Model):
    start_date = models.DateField()
    end_date = models.DateField()
    booking_start_date = models.DateField()
    booking_end_date = models.DateField()
    assessment_date = models.DateField(null=True, blank=True)
    is_active = models.BooleanField(default=False)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )
    school = models.ForeignKey(
        ScoSchool,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='school_terms'  # Optional: sets a name for the reverse relation from ScoSchool to ScoTerm
    )

    @classmethod
    def get_current_term_for_school(cls, school_id):
        today = timezone.now().date()
        return cls.objects.filter(
            school_id=school_id,
            start_date__lte=today,
            end_date__gte=today
        ).order_by('start_date').first()

    def __str__(self):
        return f"{self.id}"

    def save(self, *args, **kwargs):
        if self.is_active:
            # Set all other terms for the school to not active
            ScoTerm.objects.filter(school=self.school, is_active=True).exclude(pk=self.pk).update(is_active=False)
        super().save(*args, **kwargs)

# Contains all the bookings that have being confirmed
class ScoEnrollment(models.Model):
    lesson = models.ForeignKey(ScoLessons, on_delete=models.CASCADE)
    swimling = models.ForeignKey(Swimling, on_delete=models.CASCADE)
    term = models.ForeignKey(ScoTerm, on_delete=models.CASCADE)
    order = models.ForeignKey('schools_orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    # notes will contain origional order id from woocommerce
    notes = models.TextField(null=True, blank=True)
    # will contain origional date booked
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['term', 'lesson', 'swimling']),
        ]
        ordering = ['-term', 'lesson']

    def __str__(self):
        return f'{self.lesson.name}, {str(self.term.id)}, ' \
               f'{self.swimling.first_name}, {self.swimling.last_name}'


