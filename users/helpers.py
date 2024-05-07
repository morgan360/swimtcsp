from users.models import UserProfile, User, Swimling
from lessons_bookings.models import LessonEnrollment, Term
from schools_bookings.models import ScoEnrollment, ScoTerm
from schools.models import ScoSchool
from django.urls import reverse

def fetch_swimling_management_data(user):
    """
    Fetch and format swimling management data for a specific user.

    :param user: User instance for whom to fetch swimling data.
    :return: List of dictionaries containing swimling data.
    """
    swimlings = Swimling.objects.filter(guardian=user).prefetch_related('lessonenrollment_set')
    swimling_management_data = []
    for swimling in swimlings:
        swimling_info = {
            'first_name': swimling.first_name,
            'last_name': swimling.last_name,
            'dob': swimling.dob,
            'notes': swimling.notes,
            'sco_role_num': swimling.sco_role_num,
            'id': swimling.id,
        }
        swimling_management_data.append(swimling_info)
    return swimling_management_data


def fetch_normal_lessons_data(user, current_term_id):
    # Fetch all swimlings associated with the given user
    swimlings = Swimling.objects.filter(guardian=user).prefetch_related('lessonenrollment_set')

    # Container for all the normal lessons data
    normal_lessons_data = []

    for swimling in swimlings:
        # Fetch enrollments for the current term
        normal_enrollments = LessonEnrollment.objects.filter(
            swimling=swimling,
            term_id=current_term_id
        ).select_related('lesson')

        # Extract lesson names from enrollments
        normal_lesson_names = [enrollment.lesson.name for enrollment in normal_enrollments]

        # Determine registration status
        is_registered = normal_enrollments.exists()

        # Organize data for each swimling
        swimling_entry = {
            'swimling_id': swimling.id,
            'first_name': swimling.first_name,
            'last_name': swimling.last_name,
            'registered_lessons': normal_lesson_names,
            'is_registered': is_registered
        }

        normal_lessons_data.append(swimling_entry)

    return normal_lessons_data


def fetch_school_lessons_data(user):
    # Fetch all schools
    schools = ScoSchool.objects.all()
    school_ids = {school.sco_role_num: school for school in schools}
    # print(school_ids)

    # Fetch all active school terms indexed by school sco_role_num
    active_school_terms = ScoTerm.objects.filter(is_active=True).select_related('school')
    active_terms_by_school = {term.school.sco_role_num: term for term in active_school_terms if term.school}
    # print(active_school_terms)
    # Fetch all swimlings that are associated with any school
    swimlings = Swimling.objects.filter(
        guardian=user,
        sco_role_num__in=school_ids.keys()
    )
    # print(swimlings)
    # Container for the school lessons data
    school_lessons_data = []

    # Process each swimling and determine their enrollment status
    for swimling in swimlings:
        school = school_ids.get(swimling.sco_role_num)
        active_term = active_terms_by_school.get(swimling.sco_role_num)

        # Check enrollments in the active term for this school
        enrollments = ScoEnrollment.objects.filter(
            swimling=swimling,
            term=active_term
        ) if active_term else ScoEnrollment.objects.none()

        # Build the data entry
        entry = {
            'first_name': swimling.first_name,
            'last_name': swimling.last_name,
            'dob': swimling.dob,
            'notes': swimling.notes,
            'sco_role_num': swimling.sco_role_num,
            'edit_link': reverse('users:edit-swimling', args=[swimling.id]),
            'id': swimling.id,
            'is_registered_sco': enrollments.exists(),
            'registered_lessons_sco': [enrollment.lesson.name for enrollment in enrollments],
            'school_name': school.name if school else "Not associated with a school",
            'school_id': school.id if school else None,
            'active_term_id': active_term.id if active_term else None,  # Ensure this line is correct
            'school_term_info': {
                'term_status': 'Active' if active_term and active_term.is_active else 'Inactive',
                'term_start_date': active_term.start_date if active_term else None,
                'term_end_date': active_term.end_date if active_term else None
            }
        }
        print(active_term)
        school_lessons_data.append(entry)

    return school_lessons_data
