from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from lessons.models import Product
from users.models import Swimling
from django.utils.formats import date_format
from django.utils import timezone

# ====================================
# Models defined in this file:
# ====================================
# 1. Term
#    - Represents a school term with booking/rebooking dates.
#    - Includes methods for getting the current term and determining its booking phase.

# 2. LessonEnrollment
#    - Represents a confirmed enrollment of a swimling in a lesson for a specific term.
#    - Linked to Product (lesson), Swimling, Term, and optionally an Order.
#    - Indexed by (term, lesson, swimling) and ordered by term descending and lesson.

# 3. LessonAssignment
#    - Assigns an instructor (User in instructors group) to multiple lessons (Products) for a specific term.
#    - Uses a many-to-many relationship with Product.
# ====================================

# from lessons_orders.models import Order
# Because of circular references had to use string references instead: 'lessons_orders.Order'


class Term(models.Model):
    start_date = models.DateField(null=True, blank=True)
    end_date = models.DateField(null=True, blank=True)
    rebooking_date = models.DateField(null=True, blank=True)
    booking_date = models.DateField(null=True, blank=True)
    assessment_date = models.DateField(null=True, blank=True)  # already nullable
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"{self.id}"

    # Method to bring back formated term

    @classmethod
    def get_current_term_id(cls):
        today = timezone.now().date()
        current_term = cls.objects.filter(start_date__lte=today, end_date__gte=today).first()
        return current_term.id if current_term else None

    @classmethod
    def get_current_term(cls):
        today = timezone.now().date()
        return cls.objects.filter(
            start_date__lte=today,
            end_date__gte=today
        ).order_by('start_date').first()

    @classmethod
    def get_previous_term(cls):
        today = timezone.now().date()
        return cls.objects.filter(
            end_date__lt=today
        ).order_by('-end_date').first()

    @classmethod
    def get_next_term(cls):
        today = timezone.now().date()
        return cls.objects.filter(
            start_date__gt=today
        ).order_by('start_date').first()

    def concatenated_term(self):
        formatted_start_date = self.start_date.strftime('%d %b %Y')  # ISO format
        formatted_end_date = self.end_date.strftime('%d %b %Y')
        return f"({self.id}) - {formatted_start_date} ~ {formatted_end_date}"

    def determine_phase(self):
        today = timezone.now().date()
        current_term_id = Term.get_current_term_id()

        if self.start_date <= today < self.rebooking_date:
            return f'BK'
        elif self.rebooking_date <= today < self.booking_date:
            return f'RB'
        elif self.booking_date <= today <= self.end_date:
            return f'BN'
        else:
            return 'Outside Term Dates'

    def get_phase_code(self):
        today = timezone.now().date()
        current_term_id = Term.get_current_term_id()

        if self.start_date <= today < self.booking_date:
            return '1'  # Code for 'Booking for Current Term'
        elif self.booking_date <= today < self.rebooking_date:
            return '2'  # Code for 'Rebooking for Next Term'
        elif self.rebooking_date <= today <= self.end_date:
            return '3'  # Code for 'Booking for Next Term'
        else:
            return '0'  # Code for 'Outside Term'


# Contains all the bookings that have being confirmed
# models.py

class LessonEnrollment(models.Model):
    lesson = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='enrollments')
    swimling = models.ForeignKey(Swimling, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    order = models.ForeignKey('lessons_orders.Order', on_delete=models.CASCADE, null=True, blank=True)
    notes = models.TextField(null=True, blank=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        indexes = [
            models.Index(fields=['term', 'lesson', 'swimling']),
        ]
        ordering = ['-term', 'lesson']

    def __str__(self):
        return f'{self.lesson.name}, {str(self.term.id)}, {self.swimling.first_name}, {self.swimling.last_name}'


# Assign Instructors to Lessons for a term
class LessonAssignment(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   limit_choices_to={
                                       'groups__name': 'instructors'},
                                   related_name='assignments')  # Use a related_name
    lessons = models.ManyToManyField(Product)  # Many-to-many relationship with Lesson model

    class Meta:
        verbose_name = "Instructor Assignment"
        verbose_name_plural = "Instructor Assignments"

    def __str__(self):
        return f"Instructor {self.instructor.get_username()} assigned to {self.lessons.count()} lessons for Term {self.term}"