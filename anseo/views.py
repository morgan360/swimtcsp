from types import SimpleNamespace
from datetime import timedelta
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from lessons_bookings.models import LessonEnrollment, Term
from lessons.models import Product
from anseo.models import AttendanceEntry, AttendanceRoll
from django.db.models import Count, Q


@login_required
def take_roll(request, product_id: int, term_id: int):
    lesson = get_object_or_404(Product, pk=product_id)
    term = get_object_or_404(Term, pk=term_id)

    enrolments = (
        LessonEnrollment.objects
        .filter(lesson_id=lesson.id, term_id=term.id)
        .select_related("swimling", "lesson", "term")
        .order_by("swimling__last_name", "swimling__first_name")
    )

    if not enrolments:
        return render(request, "anseo/take_roll.html", {
            "product": lesson,
            "term": term,
            "enrolments": [],
            "roll": SimpleNamespace(
                window_start=timezone.localtime(),
                window_end=timezone.localtime() + timedelta(hours=2),
            ),
            "existing": {},
            "status_choices": AttendanceEntry.STATUS_CHOICES,
        })

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


@login_required
def attendance_history(request, product_id: int, term_id: int):
    lesson = get_object_or_404(Product.objects.select_related("category"), pk=product_id)
    term = get_object_or_404(Term, pk=term_id)

    rolls = (
        AttendanceRoll.objects
        .filter(product=lesson, term=term)
        .select_related("created_by")
        .prefetch_related("entries__enrollment__swimling")
        .order_by("-window_start")
    )

    roll_summaries = []
    status_choices = list(AttendanceEntry.STATUS_CHOICES)
    status_lookup = dict(AttendanceEntry.STATUS_CHOICES)
    for roll in rolls:
        counts = roll.entries.values("status").annotate(total=Count("id"))
        count_map = {row["status"]: row["total"] for row in counts}
        roll_summaries.append({
            "roll": roll,
            "counts": count_map,
            "total": sum(count_map.values()),
        })

    swimling_entries = (
        AttendanceEntry.objects
        .filter(roll__product=lesson, roll__term=term)
        .select_related("enrollment__swimling")
    )

    summary_by_swimling = {}
    for entry in swimling_entries:
        swimling = getattr(entry.enrollment, "swimling", None)
        swimling_id = getattr(swimling, "id", entry.swimling_id)
        if swimling_id not in summary_by_swimling:
            summary_by_swimling[swimling_id] = {
                "swimling": swimling,
                "counts": {code: 0 for code, _ in status_choices},
                "total": 0,
            }
        summary = summary_by_swimling[swimling_id]
        summary["counts"][entry.status] = summary["counts"].get(entry.status, 0) + 1
        summary["total"] += 1

    swimmer_rows = []
    for swimling_id, summary in summary_by_swimling.items():
        counts = summary["counts"]
        total = summary["total"]
        present = counts.get(AttendanceEntry.PRESENT, 0)
        attendance_pct = (present / total * 100) if total else None
        swimmer_rows.append({
            "swimling": summary["swimling"],
            "swimling_id": swimling_id,
            "counts": counts,
            "total": total,
            "attendance_pct": attendance_pct,
        })

    swimmer_rows.sort(
        key=lambda row: (
            getattr(row["swimling"], "last_name", "").lower(),
            getattr(row["swimling"], "first_name", "").lower()
        )
    )

    terms_for_lesson = list(
        Term.objects.filter(
            id__in=LessonEnrollment.objects.filter(lesson=lesson).values_list("term_id", flat=True).distinct()
        ).order_by("-start_date")
    )

    return render(
        request,
        "anseo/attendance_history.html",
        {
            "product": lesson,
            "term": term,
            "roll_summaries": roll_summaries,
            "status_choices": status_choices,
            "status_lookup": status_lookup,
            "swimmer_rows": swimmer_rows,
            "terms_for_lesson": terms_for_lesson,
        },
    )


@login_required
def attendance_matrix(request, product_id: int):
    lesson = get_object_or_404(Product.objects.select_related("category"), pk=product_id)

    term_ids = LessonEnrollment.objects.filter(lesson=lesson).values_list("term_id", flat=True).distinct()
    terms_qs = Term.objects.filter(id__in=term_ids).order_by("-start_date")
    terms_for_lesson = list(terms_qs)

    status_choices = list(AttendanceEntry.STATUS_CHOICES)
    status_lookup = dict(AttendanceEntry.STATUS_CHOICES)
    status_badges = {
        AttendanceEntry.PRESENT: "bg-green-100 text-green-700 border border-green-200",
        AttendanceEntry.ABSENT: "bg-red-100 text-red-700 border border-red-200",
        AttendanceEntry.LATE: "bg-yellow-100 text-yellow-700 border border-yellow-200",
        AttendanceEntry.EXCUSED: "bg-blue-100 text-blue-700 border border-blue-200",
        AttendanceEntry.UNKNOWN: "bg-slate-100 text-slate-600 border border-slate-200",
    }

    if not terms_for_lesson:
        return render(
            request,
            "anseo/partials/attendance_matrix.html",
            {
                "lesson": lesson,
                "terms": [],
                "selected_term": None,
                "search": request.GET.get("q", ""),
                "matrices": [],
                "status_choices": status_choices,
                "status_lookup": status_lookup,
                "status_badges": status_badges,
            },
        )

    requested_term_id = request.GET.get("term") or request.GET.get("term_id")
    selected_term = None
    if requested_term_id:
        selected_term = next((t for t in terms_for_lesson if str(t.id) == str(requested_term_id)), None)
    if selected_term is None:
        selected_term = terms_for_lesson[0]

    search = (request.GET.get("q") or "").strip()

    scoped_terms = terms_for_lesson if search else [selected_term]

    matrices = []

    for term in scoped_terms:
        rolls = list(
            AttendanceRoll.objects
            .filter(product=lesson, term=term)
            .order_by("window_start")
        )

        if not rolls:
            continue

        weeks = []
        roll_ids = []
        for idx, roll in enumerate(rolls, start=1):
            roll_ids.append(roll.id)
            weeks.append({
                "index": idx,
                "label": f"Week {idx}",
                "date": roll.window_start.date(),
            })

        enrolments_qs = (
            LessonEnrollment.objects
            .filter(lesson=lesson, term=term)
            .select_related("swimling")
        )

        if search:
            enrolments_qs = enrolments_qs.filter(
                Q(swimling__first_name__icontains=search) |
                Q(swimling__last_name__icontains=search)
            )

        enrolments = list(enrolments_qs)
        if not enrolments:
            continue

        rows_map = {}
        for enrolment in enrolments:
            swimling = enrolment.swimling
            swimling_id = getattr(swimling, "id", enrolment.swimling_id)
            rows_map[swimling_id] = {
                "swimling": swimling,
                "swimling_id": swimling_id,
                "statuses": {rid: AttendanceEntry.UNKNOWN for rid in roll_ids},
            }

        entries = AttendanceEntry.objects.filter(roll_id__in=roll_ids, enrollment__in=enrolments)
        for entry in entries:
            swimling_id = entry.enrollment.swimling_id
            row = rows_map.get(swimling_id)
            if row:
                row["statuses"][entry.roll_id] = entry.status

        rows = []
        for row in rows_map.values():
            statuses = [row["statuses"][rid] for rid in roll_ids]
            rows.append({
                "swimling": row["swimling"],
                "swimling_id": row["swimling_id"],
                "statuses": statuses,
            })

        rows.sort(
            key=lambda row: (
                getattr(row["swimling"], "last_name", "").lower(),
                getattr(row["swimling"], "first_name", "").lower(),
            )
        )

        matrices.append({
            "term": term,
            "weeks": weeks,
            "rows": rows,
        })

    return render(
        request,
        "anseo/partials/attendance_matrix.html",
        {
            "lesson": lesson,
            "terms": terms_for_lesson,
            "selected_term": selected_term,
            "search": search,
            "matrices": matrices,
            "status_choices": status_choices,
            "status_lookup": status_lookup,
            "status_badges": status_badges,
        },
    )
