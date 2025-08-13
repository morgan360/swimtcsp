from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from instructors.models import InstructorAssignment
from utils.terms_utils import get_term_context_data
from lessons.models import Product, Category
from lessons_bookings.models import Term, LessonEnrollment
from progress.models import SkillAssessment, InstructorNote, CategorySkill, Skill, CoreAquaticSkill
from users.models import Swimling
import weasyprint
from django.template.loader import render_to_string
from django.http import HttpResponse
from collections import defaultdict
from lessons_bookings.models import Term
from lessons_bookings.models import LessonEnrollment
from django.views.decorators.http import require_POST
from .forms import AssessmentFormSet, InstructorNoteForm
from django.db import transaction
from django.contrib import messages


#### START ####
@login_required
def instructor_dashboard(request):
    term_data = get_term_context_data()
    terms = [term_data.get('previous_term'), term_data.get('current_term'), term_data.get('next_term')]
    terms = [term for term in terms if term]

    assignments = (
        InstructorAssignment.objects
        .filter(instructor=request.user, term__in=terms)
        .select_related('lesson', 'term')
        .order_by('-term__start_date', 'lesson__name')
    )

    return render(request, "instructors/dashboard.html", {
        "assignments": assignments,
        "terms": terms,
    })

@transaction.atomic
@login_required
def evaluate_progress(request, swimling_id):
    # Terms this swimling was actually enrolled in
    enrollments = (
        LessonEnrollment.objects
        .filter(swimling_id=swimling_id)
        .select_related("term", "lesson", "lesson__category", "swimling")
        .order_by("term__id")
    )
    if not enrollments.exists():
        return render(request, "instructors/evaluate_progress_empty.html", {"swimling_id": swimling_id})

    # Build terms in order + map header label from the lesson's category short_name
    terms, header_map, seen = [], {}, set()
    for e in enrollments:
        if e.term_id not in seen:
            terms.append(e.term)
            seen.add(e.term_id)
        cat_short = getattr(getattr(e.lesson, "category", None), "short_name", None)
        header_map[e.term_id] = cat_short  # e.g. "Beg-1", etc. (may be None)

    swimling = enrollments.first().swimling
    current_term = terms[-1]

    # Ensure there is one SkillAssessment per skill for the current term
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

    # Past-term history (read-only)
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
        forms_by_skill = {f.instance.skill_id: f for f in formset.forms}

        cas_groups = []
        current_cas = None
        bucket = []

        for a in qs:  # qs already ordered by "skill__cas__name", "skill__name"
            cas_name = a.skill.cas.name if a.skill and a.skill.cas_id else "Uncategorised"
            f = forms_by_skill.get(a.skill_id)
            if f is None:
                continue  # (defensive) shouldn't happen

            if cas_name != current_cas:
                if bucket:
                    cas_groups.append((current_cas, bucket))
                current_cas = cas_name
                bucket = []
            bucket.append(f)

        if bucket:
            cas_groups.append((current_cas, bucket))
        existing_note = (
            InstructorNote.objects
            .filter(swimling=swimling, term=current_term)
            .values_list("note", flat=True)
            .first() or ""
        )
        note_form = InstructorNoteForm(initial={"note": existing_note})

    return render(request, "instructors/evaluate_progress.html", {
        "swimling": swimling,
        "terms": terms,
        "header_map": header_map,      # <- use in template for the sublabel
        "current_term": current_term,
        "past_terms": past_terms,
        "formset": formset,
        "note_form": note_form,
        "history_map": history_map,
        "cas_groups": cas_groups,
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
