from django.db import models
from django.conf import settings

class CoreAquaticSkill(models.Model):
    name = models.CharField(max_length=100, unique=True)  # e.g. "Aquatic Breathing"
    description = models.TextField(blank=True)

    def __str__(self):
        return self.name


class Skill(models.Model):
    code = models.CharField(max_length=20, unique=True)
    name = models.CharField(max_length=200)
    description = models.TextField(blank=True)
    cas = models.ForeignKey(CoreAquaticSkill, on_delete=models.CASCADE, related_name="skills")

    def __str__(self):
        return f"{self.code} – {self.name}"


class LessonSkill(models.Model):
    lesson = models.ForeignKey("lessons.Product", on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("lesson", "skill")
        ordering = ["order"]


class SkillAssessment(models.Model):
    swimling = models.ForeignKey('users.Swimling', on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    term = models.ForeignKey('lessons_bookings.Term', on_delete=models.CASCADE)
    instructor = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    level = models.PositiveIntegerField(choices=[(i, f"Level {i}") for i in range(1, 6)])
    notes = models.TextField(blank=True)

    class Meta:
        unique_together = ('swimling', 'skill', 'term')


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
