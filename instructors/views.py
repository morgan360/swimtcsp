from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from instructors.models import InstructorAssignment
from utils.terms_utils import get_term_context_data
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from lessons.models import Product
from lessons_bookings.models import Term, LessonEnrollment
from progress.models import SkillAssessment, InstructorNote, LessonSkill
from users.models import Swimling

@login_required
def instructor_dashboard(request):
    term_data = get_term_context_data()
    terms = [term_data.get('previous_term'), term_data.get('current_term'), term_data.get('next_term')]
    terms = [term for term in terms if term]  # Remove None if any term is missing

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


@login_required
def evaluate_lesson_skills(request, lesson_id, term_id):
    lesson = get_object_or_404(Product, id=lesson_id)
    term = get_object_or_404(Term, id=term_id)

    if not request.user.groups.filter(name='instructor').exists():
        return redirect('not_authorized')

    swimlings = Swimling.objects.filter(
        enrollments__lesson=lesson,
        enrollments__term=term
    ).distinct()

    skills = LessonSkill.objects.filter(lesson=lesson).select_related('skill')

    if request.method == 'POST':
        for swimling in swimlings:
            for lesson_skill in skills:
                level_key = f"level_{swimling.id}_{lesson_skill.skill.id}"
                notes_key = f"notes_{swimling.id}_{lesson_skill.skill.id}"

                level_val = request.POST.get(level_key)
                notes_val = request.POST.get(notes_key, '')

                if level_val:
                    SkillAssessment.objects.update_or_create(
                        swimling=swimling,
                        skill=lesson_skill.skill,
                        term=term,
                        defaults={
                            'instructor': request.user,
                            'level': int(level_val),
                            'notes': notes_val
                        }
                    )

            # Optional: Save general instructor note
            general_note = request.POST.get(f"note_{swimling.id}", "")
            if general_note:
                InstructorNote.objects.update_or_create(
                    swimling=swimling,
                    term=term,
                    defaults={
                        'instructor': request.user,
                        'note': general_note
                    }
                )

        return redirect("instructors:instructor_dashboard")

    # prefetch existing assessments
    assessments = SkillAssessment.objects.filter(term=term, swimling__in=swimlings).select_related('skill', 'swimling')
    notes = InstructorNote.objects.filter(term=term, swimling__in=swimlings)

    assessments_by_key = {
        (a.swimling_id, a.skill_id): a for a in assessments
    }
    notes_by_id = {n.swimling_id: n for n in notes}

    return render(request, "instructors/evaluate_lesson_skills.html", {
        "lesson": lesson,
        "term": term,
        "swimlings": swimlings,
        "skills": [ls.skill for ls in skills],
        "assessments": assessments_by_key,
        "notes": notes_by_id
    })
