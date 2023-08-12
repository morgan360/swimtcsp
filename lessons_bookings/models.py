from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from lessons.models import Product  # Make sure this import is correct
from users.models import Swimling  # Make sure this import is correct
from lessons_orders.models import Order  # Make sure this import is correct


class Term(models.Model):
    term_id = models.IntegerField(unique=True)
    start = models.DateField()
    end = models.DateField()
    rebooking = models.DateField()
    booking = models.DateField()
    assessments = models.DateField()
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"Term {self.term_id}"


class LessonEnrollment(models.Model):
    lesson = models.ForeignKey(Product, on_delete=models.CASCADE)
    swimling = models.ForeignKey(Swimling, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    instructor1 = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    related_name='instructor1',
                                    on_delete=models.SET_NULL, null=True)
    instructor2 = models.ForeignKey(settings.AUTH_USER_MODEL,
                                    related_name='instructor2',
                                    on_delete=models.SET_NULL, null=True)
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)
    changed_by = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.SET_NULL, null=True)

    class Meta:
        indexes = [
            models.Index(fields=['term', 'lesson', 'swimling']),
        ]
        ordering = ['-term', 'lesson']

    def __str__(self):
        return f'{self.lesson.name}, {self.term.name}, {self.swimling.name}'
