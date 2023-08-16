from django.conf import settings
from django.db import models
from django.contrib.auth.models import User
from lessons.models import Product
from users.models import Swimling


# from lessons_orders.models import Order


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
        return f'{self.lesson.name}, {str(self.term.id)}, ' \
               f'{self.swimling.first_name}, {self.swimling.last_name}'


class LessonAssignment(models.Model):
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL,
                                   on_delete=models.CASCADE,
                                   limit_choices_to={
                                       'groups__name': 'instructors'},
                                   related_name='assignments')  # Use a related_name
    lessons = models.ManyToManyField(
        Product)  # Many-to-many relationship with Lesson model

    def __str__(self):
        return f"Instructor {self.instructor.get_username()} assigned to {self.lessons.count()} lessons for Term {self.term}"
