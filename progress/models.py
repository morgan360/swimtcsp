from django.db import models
from django.conf import settings
from users.models import Swimling
from lessons_bookings.models import Term
from lessons.models import Product as Lesson
from django.contrib.auth import get_user_model
from django.db.models import Index
from django.core.validators import MinValueValidator, MaxValueValidator
User = get_user_model()


class CoreAquaticSkill(models.Model):
    abbreviation = models.CharField(max_length=10, null=True, blank=True, unique=False) # e.g. "B1", "L2"
    name = models.CharField(max_length=100)  # e.g. "Beginners 1", "Level 2"
    description = models.TextField(blank=True)

    def __str__(self):
        return f"{self.abbreviation} – {self.name}"



class Skill(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cas = models.ForeignKey(CoreAquaticSkill, on_delete=models.CASCADE, related_name="skills")

    def __str__(self):
        return f"{self.code} – {self.name}"

class CategorySkill(models.Model):
    category = models.ForeignKey("lessons.Category", on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("category", "skill")
        ordering = ["order"]

class SkillAssessment(models.Model):
    swimling = models.ForeignKey(Swimling, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    term = models.ForeignKey(Term, on_delete=models.CASCADE)
    rating = models.PositiveSmallIntegerField(
        null=True, blank=True,
        validators=[MinValueValidator(1), MaxValueValidator(5)]
    )
    lesson = models.ForeignKey(Lesson, on_delete=models.SET_NULL, null=True)
    instructor = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('swimling', 'skill', 'term')
        indexes = [
            models.Index(fields=['swimling', 'term']),
            models.Index(fields=['term', 'skill']),
        ]

    def __str__(self):
        return f"{self.swimling} – {self.skill} – {self.term}: {self.rating or '—'}"

    def clean(self):
        if self.lesson and self.lesson.term != self.term:
            raise ValidationError("Lesson term does not match assessment term.")

class InstructorNote(models.Model):
    swimling = models.ForeignKey('users.Swimling', on_delete=models.CASCADE)
    term = models.ForeignKey('lessons_bookings.Term', on_delete=models.CASCADE)
    note = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        unique_together = ('swimling', 'term')
from django.db import models

# Create your models here.
