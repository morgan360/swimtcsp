from django.conf import settings
from django.db import models
from django.utils import timezone
from datetime import timedelta

from lessons.models import Product
from lessons_bookings.models import LessonEnrollment,Term

def floor_to_8h(dt):
    # Normalize to a fixed 8h bucket: 00:00, 08:00, 16:00 in the SAME DATE
    hour_bucket = (dt.hour // 8) * 8
    return dt.replace(hour=hour_bucket, minute=0, second=0, microsecond=0)

class AttendanceRoll(models.Model):
    """
    One roll (register) per product x term x 8-hour window.
    Prevents another roll being created inside that 8-hour window.
    """
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="attendance_rolls")
    term = models.ForeignKey(Term, on_delete=models.PROTECT, related_name="attendance_rolls")

    # Start of the 8-hour window (normalized with floor_to_8h in app logic)
    window_start = models.DateTimeField()
    window_end = models.DateTimeField()

    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL, related_name="created_rolls"
    )
    created_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["-window_start"]
        constraints = [
            models.UniqueConstraint(
                fields=["product", "term", "window_start"],
                name="uniq_roll_per_product_term_per_8h_window",
            )
        ]

    @classmethod
    def get_or_create_current(cls, *, product, term, user=None, now=None):
        now = now or timezone.now()
        ws = floor_to_8h(now)
        we = ws + timedelta(hours=8)
        roll, created = cls.objects.get_or_create(
            product=product, term=term, window_start=ws,
            defaults={"window_end": we, "created_by": user}
        )
        return roll, created

    def locked(self):
        # optional: lock editing once the window passes
        return timezone.now() > self.window_end

class AttendanceEntry(models.Model):
    PRESENT = "present"
    ABSENT  = "absent"
    LATE    = "late"
    EXCUSED = "excused"
    UNKNOWN = "unknown"
    STATUS_CHOICES = [
        (PRESENT, "Present"),
        (ABSENT, "Absent"),
        (LATE, "Late"),
        (EXCUSED, "Excused"),
        (UNKNOWN, "Not Marked"),
    ]

    roll = models.ForeignKey(AttendanceRoll, on_delete=models.CASCADE, related_name="entries")
    enrollment = models.ForeignKey(LessonEnrollment, on_delete=models.CASCADE, related_name="attendance_entries")
    swimling_id = models.IntegerField()  # denormalize for speed; keep in sync from enrolment
    status = models.CharField(max_length=16, choices=STATUS_CHOICES, default=UNKNOWN)
    marked_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="attendance_marks"
    )
    marked_at = models.DateTimeField(default=timezone.now)
    note = models.CharField(max_length=255, blank=True)

    class Meta:
        unique_together = [("roll", "enrollment")]
        indexes = [models.Index(fields=["roll", "enrollment"])]
