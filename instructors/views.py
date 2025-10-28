from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from types import SimpleNamespace
from datetime import date as dt_date, time as dt_time
from instructors.models import InstructorAssignment
from utils.terms_utils import get_term_context_data
from lessons.models import Product, Category
from lessons_bookings.models import Term, LessonEnrollment, LessonAssignment
from progress.models import SkillAssessment, InstructorNote, CategorySkill, Skill, CoreAquaticSkill
from users.models import Swimling
import weasyprint
from django.template.loader import render_to_string
from django.http import HttpResponse
from collections import defaultdict, OrderedDict
from django.db.models import Count, Prefetch
from django.views.decorators.http import require_POST
from .forms import AssessmentFormSet, InstructorNoteForm
from django.db import transaction
from django.contrib import messages


#### START ####
@login_required
def instructor_dashboard(request):
    term_data = get_term_context_data()
    current_term = term_data.get('current_term')
    terms = [term_data.get('previous_term'), current_term, term_data.get('next_term')]
    terms = [term for term in terms if term]

    direct_assignments_qs = (
        InstructorAssignment.objects
        .filter(instructor=request.user, term__in=terms)
        .select_related('lesson__category', 'term')
    )

    assignments = list(direct_assignments_qs)
    seen_pairs = {(assignment.lesson_id, assignment.term_id) for assignment in assignments}

    lesson_assignments = (
        LessonAssignment.objects
        .filter(instructor=request.user, term__in=terms)
        .select_related('term', 'instructor')
        .prefetch_related(
            Prefetch('lessons', queryset=Product.objects.select_related('category'))
        )
    )

    for assignment in lesson_assignments:
        for lesson in assignment.lessons.all():
            lesson_id = getattr(lesson, 'id', None)
            term_id = assignment.term_id
            if not lesson_id or (lesson_id, term_id) in seen_pairs:
                continue
            assignments.append(SimpleNamespace(
                id=None,
                lesson=lesson,
                lesson_id=lesson_id,
                term=assignment.term,
                term_id=term_id,
                instructor=assignment.instructor,
                source='lesson_assignment'
            ))
            seen_pairs.add((lesson_id, term_id))

    assignments.sort(
        key=lambda a: (
            getattr(a.term, 'start_date', None) or dt_date.min,
            getattr(a.lesson, 'day_of_week', None) if getattr(a.lesson, 'day_of_week', None) is not None else 0,
            getattr(a.lesson, 'start_time', None) or dt_time.min
        ),
        reverse=True
    )

    lesson_ids = {a.lesson_id for a in assignments if getattr(a, 'lesson_id', None)}
    term_ids = {a.term_id for a in assignments if getattr(a, 'term_id', None)}

    total_students = 0
    enrollment_counts = {}
    if lesson_ids and term_ids:
        enrollment_rows = (
            LessonEnrollment.objects
            .filter(
                lesson_id__in=lesson_ids,
                term_id__in=term_ids
            )
            .values('lesson_id', 'term_id')
            .annotate(total=Count('id'))
        )
        enrollment_counts = {
            (row['lesson_id'], row['term_id']): row['total']
            for row in enrollment_rows
        }
        total_students = sum(enrollment_counts.values())
    for assignment in assignments:
        assignment.enrolled_count = enrollment_counts.get(
            (getattr(assignment, 'lesson_id', None), getattr(assignment, 'term_id', None)),
            0
        )

    grouped = OrderedDict()
    for assignment in assignments:
        term = getattr(assignment, 'term', None)
        key = f"term-{getattr(term, 'id', 'unassigned')}" if term else 'unassigned'
        if key not in grouped:
            grouped[key] = {
                "term": term,
                "assignments": []
            }
        grouped[key]["assignments"].append(assignment)
    assignment_groups = list(grouped.values())

    current_term_id = getattr(current_term, 'id', None)
    lessons_this_week = sum(1 for a in assignments if getattr(a, 'term_id', None) == current_term_id)

    return render(request, "instructors/dashboard.html", {
        "assignments": assignments,
        "assignment_groups": assignment_groups,
        "terms": terms,
        "total_students": total_students,
        "lessons_this_week": lessons_this_week,
    })

def stage_key(label: str):
    STAGE_ORDER = ["Stage 1", "Stage 2", "Stage 3", "Stage 4", "Stage 5", "Stage 6",
                   "Stage 7", "Stage 8", "Stage 9", "Stage 10", ""]
    try:
        return STAGE_ORDER.index(label or "")
    except ValueError:
        return len(STAGE_ORDER)

@transaction.atomic
@login_required
def evaluate_progress(request, swimling_id):
    enrollments = (
        LessonEnrollment.objects
        .filter(swimling_id=swimling_id)
        .select_related("term", "lesson", "lesson__category", "swimling")
        .order_by("term__id")
    )
    if not enrollments.exists():
        return render(request, "instructors/evaluate_progress_empty.html", {"swimling_id": swimling_id})

    terms, header_map, seen = [], {}, set()
    for e in enrollments:
        if e.term_id not in seen:
            terms.append(e.term)
            seen.add(e.term_id)
        cat_short = getattr(getattr(e.lesson, "category", None), "short_name", None)
        header_map[e.term_id] = cat_short

    swimling = enrollments.first().swimling
    current_term = terms[-1]

    skills = Skill.objects.select_related("cas").order_by("cas__name", "name")
    existing = SkillAssessment.objects.filter(swimling=swimling, term=current_term)
    existing_by_skill = {a.skill_id: a for a in existing}
    to_create = [
        SkillAssessment(swimling=swimling, term=current_term, skill=s)
        for s in skills if s.id not in existing_by_skill
    ]
    if to_create:
        SkillAssessment.objects.bulk_create(to_create)

    qs = (
        SkillAssessment.objects
        .filter(swimling=swimling, term=current_term)
        .select_related("skill", "skill__cas")
        .order_by("skill__cas__name", "skill__name")
    )

    past_terms = [t for t in terms if t.id != current_term.id]
    history_map = {}
    if past_terms:
        rows = (
            SkillAssessment.objects
            .filter(swimling=swimling, term__in=past_terms)
            .values("skill_id", "term_id", "rating")
        )
        for r in rows:
            history_map.setdefault(r["skill_id"], {})[r["term_id"]] = r["rating"]

    if request.method == "POST":
        formset = AssessmentFormSet(request.POST, queryset=qs, prefix="assess")
        note_form = InstructorNoteForm(request.POST)
        if formset.is_valid() and note_form.is_valid():
            with transaction.atomic():
                formset.save()
                InstructorNote.objects.update_or_create(
                    swimling=swimling,
                    term=current_term,
                    defaults={"note": note_form.cleaned_data.get("note", "")},
                )
            messages.success(request, "Progress saved.")
            return redirect("instructors:evaluate_progress", swimling_id=swimling.id)
    else:
        formset = AssessmentFormSet(queryset=qs, prefix="assess")
        existing_note = (
            InstructorNote.objects
            .filter(swimling=swimling, term=current_term)
            .values_list("note", flat=True)
            .first() or ""
        )
        note_form = InstructorNoteForm(initial={"note": existing_note})

    from collections import defaultdict

    # ...

    forms_by_skill = {f.instance.skill_id: f for f in formset.forms}
    cat_skill_map = {
        cs.skill_id: cs.category for cs in CategorySkill.objects.select_related("category")
    }

    cas_stage_form_map = defaultdict(lambda: defaultdict(list))

    for a in qs:
        form = forms_by_skill.get(a.skill_id)
        if not form:
            continue

        skill = a.skill
        cas_name = skill.cas.name if skill.cas else "Uncategorised"
        stage = cat_skill_map.get(a.skill_id).stage if cat_skill_map.get(a.skill_id) else ""
        stage = stage or "Uncategorised"

        cas_stage_form_map[cas_name][stage].append(form)

    # Sort stages within each CAS
    cas_groups_staged = [
        (cas_name, sorted(stages.items(), key=lambda kv: stage_key(kv[0])))
        for cas_name, stages in cas_stage_form_map.items()
    ]

    return render(request, "instructors/evaluate_progress.html", {
        "swimling": swimling,
        "terms": terms,
        "header_map": header_map,
        "current_term": current_term,
        "past_terms": past_terms,
        "formset": formset,
        "note_form": note_form,
        "history_map": history_map,
        "cas_groups_staged": cas_groups_staged,
    })

#### UNSURE ####
def evaluate_swimling_progress(request, swimling_id):
    swimling = get_object_or_404(Swimling, id=swimling_id)

    # Terms the swimling is enrolled in
    enrollments = (
        LessonEnrollment.objects
        .filter(swimling=swimling)
        .select_related("term", "lesson__category")
    )
    terms = sorted({e.term for e in enrollments}, key=lambda t: t.start_date)

    # Map each term -> lesson short name (if available)
    lesson_map = {}
    for e in enrollments:
        if e.lesson and getattr(e.lesson, "category", None):
            lesson_map[e.term.id] = e.lesson.category.short_name

    # Skills/CAS lists
    cas_list = CoreAquaticSkill.objects.prefetch_related("skills").all()
    # assessments nested dict: assessments[skill_id][term_id] = SkillAssessment
    assessments = defaultdict(dict)
    for a in SkillAssessment.objects.filter(swimling=swimling):
        assessments[a.skill_id][a.term_id] = a

    # notes map: notes[term_id] = InstructorNote
    notes = {n.term_id: n for n in InstructorNote.objects.filter(swimling=swimling)}

    # Only the notes form posts here; ratings are saved via HTMX in update_skill_rating
    if request.method == "POST":
        for term in terms:
            key = f"note_{term.id}"
            note_val = request.POST.get(key)
            if note_val is None:
                continue  # field not present
            note_text = note_val.strip()
            if note_text == "":
                # Optional: blank deletes note
                InstructorNote.objects.filter(swimling=swimling, term=term).delete()
            else:
                InstructorNote.objects.update_or_create(
                    swimling=swimling,
                    term=term,
                    defaults={"instructor": request.user, "note": note_text},
                )
        return redirect("instructors:evaluate_swimling_progress", swimling_id=swimling.id)

    return render(
        request,
        "instructors/evaluate_swimling_progress.html",
        {
            "swimling": swimling,
            "terms": terms,
            "cas_list": cas_list,
            "assessments": assessments,
            "notes": notes,
            "lesson_map": lesson_map,
        },
    )### Skill Charts ###

def category_skill_matrix(request):
    # Categories and their skills
    categories = Category.objects.prefetch_related(
        'categoryskill_set__skill'
    ).all()

    # CAS and their skills (optional)
    cas_list = CoreAquaticSkill.objects.prefetch_related('skills').all()

    return render(request, 'instructors/category_skill_matrix.html', {
        'categories': categories,
        'cas_list': cas_list,
    })

def generate_skill_report(request, swimling_id):
    swimling = get_object_or_404(Swimling, id=swimling_id)

    # Only terms that have assessments for this swimling, ordered by start
    terms = (
        Term.objects
        .filter(skillassessment__swimling=swimling)
        .distinct()
        .order_by("start_date")
    )

    assessments = (
        SkillAssessment.objects
        .filter(swimling=swimling)
        .select_related("skill__cas", "term")
    )
    notes = (
        InstructorNote.objects
        .filter(swimling=swimling)
        .select_related("term")
        .order_by("term__start_date")
    )

    # Build CAS -> Skill -> {term_id: rating}
    nested = defaultdict(lambda: defaultdict(dict))
    for a in assessments:
        nested[a.skill.cas.name][a.skill.name][a.term_id] = a.rating  # rating may be None

    # Make it template‑friendly and sorted
    report_rows = []
    for cas_name, skills_map in sorted(nested.items()):
        skill_rows = []
        for skill_name, ratings_map in sorted(skills_map.items()):
            # normalize per-term dict so template access is simple
            ratings_by_term = {t.id: ratings_map.get(t.id) for t in terms}
            skill_rows.append((skill_name, ratings_by_term))
        report_rows.append((cas_name, skill_rows))

    html_string = render_to_string(
        "instructors/skill_report_template.html",
        {
            "swimling": swimling,
            "terms": terms,
            "notes": notes,
            "report_rows": report_rows,   # <— use this in template
        },
    )
    pdf_file = weasyprint.HTML(string=html_string).write_pdf()
    return HttpResponse(pdf_file, content_type="application/pdf")
@login_required
def lesson_swimlings(request, lesson_id, term_id):
    # Ensure this lesson+term is assigned to the current instructor
    assignment = get_object_or_404(
        InstructorAssignment.objects.select_related("lesson", "term"),
        instructor=request.user,
        lesson_id=lesson_id,
        term_id=term_id,
    )

    # Enrollments for that lesson & term (deduplicate by swimling)
    enrollments = (
        LessonEnrollment.objects
        .filter(lesson_id=lesson_id, term_id=term_id)
        .select_related("swimling")
        .order_by("swimling__last_name", "swimling__first_name", "id")
    )

    # de-dupe per swimling_id (MySQL doesn’t support DISTINCT ON)
    seen = set()
    unique_enrollments = []
    for e in enrollments:
        if e.swimling_id not in seen:
            seen.add(e.swimling_id)
            unique_enrollments.append(e)

    return render(request, "instructors/lesson_swimlings.html", {
        "assignment": assignment,
        "enrollments": unique_enrollments,
    })
