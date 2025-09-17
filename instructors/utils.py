from typing import Optional

from django.db import transaction

from lessons_bookings.models import Term, LessonAssignment
from instructors.models import InstructorAssignment
from lessons.models import Product


def _get_latest_source_term() -> Optional[Term]:
    """Pick a sensible source term to copy from: prefer current, else previous."""
    return Term.get_current_term() or Term.get_previous_term()


@transaction.atomic
def prefill_next_term_instructors() -> int:
    """
    Copy instructor assignments from the latest active term to the next term.

    Rules:
    - If a lesson already has an assignment for the next term (either via
      InstructorAssignment or LessonAssignment), it is left untouched.
    - Otherwise, carry forward the same instructor from the source term.
    - Supports both assignment models used in the project.

    Returns the number of lesson assignments created for the next term.
    """
    created_count = 0

    source_term = _get_latest_source_term()
    next_term = Term.get_next_term()
    if not source_term or not next_term or source_term == next_term:
        return 0

    # 1) Carry forward direct per-lesson assignments (InstructorAssignment)
    src_direct = (
        InstructorAssignment.objects
        .select_related("instructor", "lesson")
        .filter(term=source_term)
    )
    for ia in src_direct:
        lesson = ia.lesson
        # Skip if already assigned for next term by either model
        if InstructorAssignment.objects.filter(term=next_term, lesson=lesson).exists():
            continue
        if LessonAssignment.objects.filter(term=next_term, lessons=lesson).exists():
            continue
        # Create a mirror InstructorAssignment for the next term
        InstructorAssignment.objects.create(
            instructor=ia.instructor,
            lesson=lesson,
            term=next_term,
        )
        created_count += 1

    # 2) Carry forward many-to-many assignments (LessonAssignment)
    src_grouped = (
        LessonAssignment.objects
        .select_related("instructor", "term")
        .prefetch_related("lessons")
        .filter(term=source_term)
    )
    for la in src_grouped:
        for lesson in la.lessons.all():
            # Skip if already assigned for next term by either model
            if InstructorAssignment.objects.filter(term=next_term, lesson=lesson).exists():
                continue
            if LessonAssignment.objects.filter(term=next_term, lessons=lesson).exists():
                continue
            # Get/create a LessonAssignment bucket for (next_term, instructor)
            next_la, _ = LessonAssignment.objects.get_or_create(
                term=next_term, instructor=la.instructor
            )
            next_la.lessons.add(lesson)
            created_count += 1

    return created_count

