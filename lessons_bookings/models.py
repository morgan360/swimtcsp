from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from lessons.models import Product
from users.models import Swimling
from django.utils.formats import date_format
# from lessons_orders.models import Order
# Because of circular references had to use string references instead: 'lessons_orders.Order'


class Term(models.Model):

    start_date = models.DateField()
    end_date = models.DateField()
    rebooking_date = models.DateField()
    booking_date = models.DateField()
    assessment_date = models.DateField( null=True,)
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

    def concatenated_term(self):
        formatted_start_date = date_format(self.start_date, "SHORT_DATE_FORMAT")
        formatted_end_date = date_format(self.end_date, "SHORT_DATE_FORMAT")
        return f"({self.id}) - {formatted_start_date} - {formatted_end_date}"

# Contains all the bookings that have being confirmed
class LessonEnrollment(models.Model):
    lesson = models.ForeignKey(Product, on_delete=models.CASCADE)
    swimling = models.ForeignKey(Swimling, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    order = models.ForeignKey('lessons_orders.Order', on_delete=models.CASCADE, null=True, blank=True)
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

# Assign Instructors to Lessons for a term
class LessonAssignment(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   limit_choices_to={
                                       'groups__name': 'instructors'},
                                   related_name='assignments')  # Use a related_name
    lessons = models.ManyToManyField(Product)  # Many-to-many relationship with Lesson model

    def __str__(self):
        return f"Instructor {self.instructor.get_username()} assigned to {self.lessons.count()} lessons for Term {self.term}"
