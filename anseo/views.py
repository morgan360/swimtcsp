from types import SimpleNamespace
from datetime import date, datetime, time, timedelta, timezone as dt_timezone
from django.contrib import messages
from django.db import transaction
from django.http import Http404
from django.shortcuts import render, redirect, get_object_or_404
from django.utils import timezone

from instructors.models import InstructorAssignment
from lessons_bookings.models import LessonAssignment, LessonEnrollment, Term
from lessons.models import Product
from anseo.models import AttendanceEntry, AttendanceRoll
from django.db.models import Count, Q
from timetable.closures import closure_for, closures_between
from utils.decorators import staff_or_instructor_required

# Classes this many days back still show as missed on the phone register list.
REGISTER_DAYS_BACK = 6


def _save_entries(roll, enrolments, post, user):
    """Write one register's submitted statuses; returns (created, updated, deleted)."""
    created = updated = deleted = 0
    valid = {code for code, _ in AttendanceEntry.STATUS_CHOICES}
    with transaction.atomic():
        for e in enrolments:
            status = (post.get(f"status_{e.id}", "") or "").strip()
            note = (post.get(f"note_{e.id}", "") or "").strip()

            if status not in valid or status == AttendanceEntry.UNKNOWN:
                cnt, _ = AttendanceEntry.objects.filter(roll=roll, enrollment=e).delete()
                deleted += cnt
                continue

            defaults = {
                "status": status,
                "note": note,
                "marked_by": user,
                "swimling_id": e.swimling_id,
            }

            obj, was_created = AttendanceEntry.objects.update_or_create(
                roll=roll,
                enrollment=e,
                defaults=defaults,
            )
            created += int(was_created)
            updated += int(not was_created)
    return created, updated, deleted


@staff_or_instructor_required
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
        created, updated, deleted = _save_entries(roll, enrolments, request.POST, request.user)

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


def _local_midnight(day):
    return timezone.make_aware(datetime.combine(day, time.min))


def _class_day(roll_date, day_of_week):
    """The class a roll belongs to: its lesson's latest weekday on or before the roll.

    The take_roll page dates a roll when it is marked, so a Saturday class caught
    up on the Monday still counts for that Saturday.
    """
    return roll_date - timedelta(days=(roll_date.weekday() - day_of_week) % 7)


def _my_lesson_ids(user, term):
    direct = InstructorAssignment.objects.filter(instructor=user, term=term).values_list("lesson_id", flat=True)
    grouped = (LessonAssignment.objects.filter(instructor=user, term=term)
               .values_list("lessons__id", flat=True))
    return set(direct) | {lesson_id for lesson_id in grouped if lesson_id}


@staff_or_instructor_required
def registers(request):
    """The phone home screen: today's classes, then any missed in the past week."""
    today = timezone.localdate()
    current_time = timezone.localtime().time()
    first_day = today - timedelta(days=REGISTER_DAYS_BACK)
    closures = closures_between(first_day, today)
    show_all = request.GET.get("all") == "1"

    marked = set()
    marked_rolls = (AttendanceEntry.objects.exclude(status=AttendanceEntry.UNKNOWN)
                    .filter(roll__window_start__gte=_local_midnight(first_day))
                    .values_list("roll__product_id", "roll__product__day_of_week", "roll__window_start")
                    .distinct())
    for product_id, day_of_week, window_start in marked_rolls:
        marked.add((product_id, _class_day(timezone.localtime(window_start).date(), day_of_week)))

    has_own_classes = False
    today_rows, missed_rows = [], []
    for offset in range(REGISTER_DAYS_BACK + 1):
        day = today - timedelta(days=offset)
        term = Term.objects.filter(start_date__lte=day, end_date__gte=day).first()
        if not term or closure_for("lesson", day, closures):
            continue
        classes = (LessonEnrollment.objects.filter(term=term, lesson__day_of_week=day.weekday())
                   .values("lesson_id", "lesson__name", "lesson__start_time")
                   .annotate(swimmers=Count("id"))
                   .order_by("lesson__start_time", "lesson__name"))
        mine = _my_lesson_ids(request.user, term)
        has_own_classes = has_own_classes or bool(mine)
        for row in classes:
            if not show_all and mine and row["lesson_id"] not in mine:
                continue
            start = row["lesson__start_time"]
            entry = {
                "lesson_id": row["lesson_id"],
                "name": row["lesson__name"],
                "time": start,
                "swimmers": row["swimmers"],
                "day": day,
                "done": (row["lesson_id"], day) in marked,
                "not_started": day == today and bool(start) and start > current_time,
            }
            if day == today:
                today_rows.append(entry)
            elif not entry["done"]:
                missed_rows.append(entry)

    return render(request, "anseo/registers.html", {
        "today": today,
        "today_rows": today_rows,
        "missed_rows": missed_rows,
        "show_all": show_all,
        "has_own_classes": has_own_classes,
    })


@staff_or_instructor_required
def phone_roll(request, product_id: int, day: str):
    """One class's register, for one date, however long after the class it is marked."""
    lesson = get_object_or_404(Product, pk=product_id)
    try:
        class_day = date.fromisoformat(day)
    except ValueError:
        raise Http404("Not a date")
    term = Term.objects.filter(start_date__lte=class_day, end_date__gte=class_day).first()
    if not term or class_day.weekday() != lesson.day_of_week or class_day > timezone.localdate():
        raise Http404("No class on that date")

    enrolments = (
        LessonEnrollment.objects
        .filter(lesson=lesson, term=term)
        .select_related("swimling")
        .order_by("swimling__last_name", "swimling__first_name")
    )
    if not enrolments:
        raise Http404("Nobody is enrolled in that class")

    # Reuse the class's roll if the tablet has already started one, or marking
    # on both would split that class's register in two.
    roll = (AttendanceRoll.objects
            .filter(product=lesson, term=term,
                    window_start__gte=_local_midnight(class_day),
                    window_start__lt=_local_midnight(class_day + timedelta(days=7)))
            .annotate(marks=Count("entries"))
            .order_by("-marks", "window_start")
            .first())

    if request.method == "POST":
        if roll is None:
            class_start = timezone.make_aware(datetime.combine(class_day, lesson.start_time or time(12)))
            # floor_to_8h buckets on the clock it is given, and rolls are bucketed in UTC.
            roll, _ = AttendanceRoll.get_or_create_current(
                product=lesson, term=term, user=request.user,
                now=class_start.astimezone(dt_timezone.utc),
            )
        _save_entries(roll, enrolments, request.POST, request.user)
        counts = {code: 0 for code, _ in AttendanceEntry.STATUS_CHOICES}
        for status in roll.entries.values_list("status", flat=True):
            counts[status] += 1
        messages.success(
            request,
            f"Saved {lesson.name}: {counts[AttendanceEntry.PRESENT]} here, "
            f"{counts[AttendanceEntry.ABSENT]} absent, {counts[AttendanceEntry.LATE]} late, "
            f"{counts[AttendanceEntry.EXCUSED]} excused.",
        )
        return redirect("anseo:registers")

    existing = {}
    if roll:
        existing = {entry.enrollment_id: entry for entry in roll.entries.all()}
    rows = []
    for e in enrolments:
        entry = existing.get(e.id)
        # Most swimmers turn up, so an instructor only has to tap the exceptions.
        status = entry.status if entry and entry.status != AttendanceEntry.UNKNOWN else AttendanceEntry.PRESENT
        rows.append({"enrolment": e, "status": status, "note": entry.note if entry else ""})

    return render(request, "anseo/phone_roll.html", {
        "lesson": lesson,
        "class_day": class_day,
        "rows": rows,
        "already_saved": bool(existing),
        "statuses": [
            (AttendanceEntry.PRESENT, "Here"),
            (AttendanceEntry.ABSENT, "Absent"),
            (AttendanceEntry.LATE, "Late"),
            (AttendanceEntry.EXCUSED, "Excused"),
        ],
    })


@staff_or_instructor_required
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


@staff_or_instructor_required
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
