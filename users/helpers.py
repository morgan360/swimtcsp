from users.models import UserProfile, User, Swimling
from lessons_bookings.models import LessonEnrollment, Term
from schools_bookings.models import ScoEnrollment, ScoTerm
from schools.models import ScoSchool
from django.urls import reverse
from waiting_list.models import WaitingList
from lessons.models import Product


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

    # Get the next term
    current_term = Term.objects.get(id=current_term_id)
    next_term = Term.objects.filter(start_date__gt=current_term.end_date).order_by('start_date').first()

    # Container for all the normal lessons data
    normal_lessons_data = []

    for swimling in swimlings:
        # Fetch enrollments for the current term
        normal_enrollments = LessonEnrollment.objects.filter(
            swimling=swimling,
            term_id=current_term_id
        ).select_related('lesson')

        # Extract lesson names and IDs from enrollments
        normal_lessons = [{
            'name': enrollment.lesson.name,
            'id': enrollment.lesson.id
        } for enrollment in normal_enrollments]

        # Determine registration status for the current term
        is_registered = normal_enrollments.exists()

        # Determine registration status for the next term
        is_registered_next_term = False
        if next_term:
            next_term_enrollments = LessonEnrollment.objects.filter(
                swimling=swimling,
                term=next_term
            )
            is_registered_next_term = next_term_enrollments.exists()

        # Organize data for each swimling
        swimling_entry = {
            'swimling_id': swimling.id,
            'first_name': swimling.first_name,
            'last_name': swimling.last_name,
            'registered_lessons': normal_lessons,  # This now includes lesson names and IDs
            'is_registered': is_registered,
            'is_registered_next_term': is_registered_next_term,
        }

        normal_lessons_data.append(swimling_entry)

    return normal_lessons_data


def fetch_school_lessons_data(user):
    # Fetch all schools
    schools = ScoSchool.objects.all()
    school_ids = {school.sco_role_num: school for school in schools}

    # Debugging prints
    print(f"Total schools: {schools.count()}")

    # Fetch all active school terms indexed by school sco_role_num
    active_school_terms = ScoTerm.objects.filter(is_active=True).select_related('school')
    active_terms_by_school = {term.school.sco_role_num: term for term in active_school_terms if term.school}

    # Debugging prints
    print(f"Active school terms: {active_school_terms.count()}")

    # Fetch all swimlings that are associated with any school
    swimlings = Swimling.objects.filter(
        guardian=user,
        sco_role_num__in=school_ids.keys()
    )

    # Debugging prints
    print(f"Swimlings under user: {swimlings.count()}")

    # Container for the school lessons data
    school_lessons_data = []

    # Process each swimling and determine their enrollment status
    for swimling in swimlings:
        school = school_ids.get(swimling.sco_role_num)
        active_term = active_terms_by_school.get(swimling.sco_role_num)

        # Debugging prints
        if not active_term:
            print(f"No active term for sco_role_num: {swimling.sco_role_num}")

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
            'active_term_id': active_term.id if active_term else None,
            'active_term': active_term,
            'school_term_info': {
                'term_status': 'Active' if active_term and active_term.is_active else 'Inactive',
                'term_start_date': active_term.start_date if active_term else None,
                'term_end_date': active_term.end_date if active_term else None
            }
        }

        school_lessons_data.append(entry)

    return school_lessons_data


def fetch_waiting_list_data(user):
    waiting_list_entries = WaitingList.objects.filter(user=user).select_related('product', 'swimling', 'assigned_lesson')
    waiting_list_data = []

    for entry in waiting_list_entries:
        waiting_list_data.append({
            'id': entry.id,
            'swimling_id': entry.swimling.id,  # Include swimling_id here
            'swimling_name': f"{entry.swimling.first_name} {entry.swimling.last_name}",
            'requested_lesson': entry.product.name,
            'assigned_lesson': entry.assigned_lesson.name if entry.assigned_lesson else "Not assigned",
            'assigned_lesson_id': entry.assigned_lesson.id if entry.assigned_lesson else None,
            'can_book': entry.is_notified
        })

    return waiting_list_data


