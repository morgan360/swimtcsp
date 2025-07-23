from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from instructors.models import InstructorAssignment
from utils.terms_utils import get_term_context_data
from lessons.models import Product, Category
from lessons_bookings.models import Term, LessonEnrollment
from progress.models import SkillAssessment, InstructorNote, CategorySkill, Skill, CoreAquaticSkill
from users.models import Swimling

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

    # Get skills for the lesson's category
    if not lesson.category:
        return render(request, "instructors/error.html", {
            "message": "This lesson has no associated category, so no skills can be evaluated."
        })

    category_skills = CategorySkill.objects.filter(category=lesson.category).select_related('skill')

    if request.method == 'POST':
        for swimling in swimlings:
            for category_skill in category_skills:
                level_key = f"level_{swimling.id}_{category_skill.skill.id}"
                notes_key = f"notes_{swimling.id}_{category_skill.skill.id}"

                level_val = request.POST.get(level_key)
                notes_val = request.POST.get(notes_key, '')

                if level_val:
                    SkillAssessment.objects.update_or_create(
                        swimling=swimling,
                        skill=category_skill.skill,
                        term=term,
                        defaults={
                            'instructor': request.user,
                            'level': int(level_val),
                            'notes': notes_val
                        }
                    )

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
        "skills": [cs.skill for cs in category_skills],
        "assessments": assessments_by_key,
        "notes": notes_by_id
    })

### Skill Charts ###

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
