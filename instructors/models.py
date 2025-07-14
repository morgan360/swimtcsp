from django.db import models
from django.conf import settings
from lessons.models import Product  # ✅ Product is the lesson
from lessons_bookings.models import Term

class InstructorAssignment(models.Model):
    instructor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        limit_choices_to={'groups__name': 'instructor'}
    )
    lesson = models.ForeignKey(Product, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('lesson', 'term')  # One instructor per lesson per term

    def __str__(self):
        return f"{self.lesson} ({self.term.label}) → {self.instructor.first_name} {self.instructor.last_name}"  # label = friendly display

class InstructorProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    qualification_level = models.CharField(max_length=20, choices=[
        ('Level 1', 'Assistant Swimming Teacher'),
        ('Level 2', 'Swimming Teacher')
    ])
    bio = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.user.get_full_name()
