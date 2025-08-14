from types import SimpleNamespace
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect
from django.utils import timezone

from lessons_bookings.models import LessonEnrollment
from anseo.models import AttendanceEntry, AttendanceRoll


@login_required
def take_roll(request, product_id: int, term_id: int):
    enrolments = (
        LessonEnrollment.objects
        .filter(lesson_id=product_id, term_id=term_id)
        .select_related("swimling", "lesson", "term")
        .order_by("swimling__last_name", "swimling__first_name")
    )

    if not enrolments:
        return render(request, "anseo/take_roll.html", {
            "product": None,
            "term": None,
            "enrolments": [],
            "roll": SimpleNamespace(
                window_start=timezone.localtime(),
                window_end=timezone.localtime() + timedelta(hours=2),
            ),
            "existing": {},
            "status_choices": AttendanceEntry.STATUS_CHOICES,
        })

    lesson = enrolments[0].lesson
    term = enrolments[0].term

    # Always get the roll for the current window
    roll, _ = AttendanceRoll.get_or_create_current(
        product=lesson,
        term=term,
        user=request.user
    )

    if request.method == "POST":
        created = updated = deleted = 0
        with transaction.atomic():
            for e in enrolments:
                status = (request.POST.get(f"status_{e.id}", "") or "").strip()
                note = (request.POST.get(f"note_{e.id}", "") or "").strip()

                if not status or status == "unknown":
                    cnt, _ = AttendanceEntry.objects.filter(roll=roll, enrollment=e).delete()
                    deleted += cnt
                    continue

                defaults = {
                    "status": status,
                    "note": note,
                    "marked_by": request.user,
                    "swimling_id": e.swimling_id,
                }

                obj, was_created = AttendanceEntry.objects.update_or_create(
                    roll=roll,
                    enrollment=e,
                    defaults=defaults,
                )
                created += int(was_created)
                updated += int(not was_created)

        messages.success(request, f"Attendance saved — {created} new, {updated} updated, {deleted} cleared.")
        return redirect("anseo:take_roll", product_id=product_id, term_id=term_id)

    # Preload existing entries
    existing = {
        ae.enrollment_id: ae
        for ae in AttendanceEntry.objects.filter(roll=roll, enrollment__in=enrolments)
    }

    return render(
        request,
        "anseo/take_roll.html",
        {
            "product": lesson,
            "term": term,
            "enrolments": enrolments,
            "roll": roll,
            "existing": existing,
            "status_choices": AttendanceEntry.STATUS_CHOICES,
        },
    )
