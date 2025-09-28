from collections import defaultdict
from users.models import  User, Swimling
from lessons_bookings.models import LessonEnrollment, Term
from schools_bookings.models import ScoEnrollment, ScoTerm
from schools.models import ScoSchool
from django.urls import reverse
from waiting_list.models import WaitingList
from lessons.models import Product
from django.utils.timezone import now

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

###  WAITING LIST ###

def fetch_waiting_list_data(user):
    today = now().date()

    waiting_list_entries = WaitingList.objects.filter(
        swimling__guardian=user,
        completed=False
    ).select_related(
        'swimling',
        'preferred_lesson_1',
        'preferred_lesson_2',
        'preferred_lesson_3',
        'assigned_lesson'
    )

    waiting_list_data = []

    for entry in waiting_list_entries:
        swimling = entry.swimling
        guardian = swimling.guardian
        current_term_id = Term.get_current_term_id()

        if current_term_id:
            has_enrolled_sibling = LessonEnrollment.objects.filter(
                swimling__guardian=guardian,
                term_id=current_term_id
            ).exclude(
                swimling=swimling
            ).exists()
        else:
            has_enrolled_sibling = False

        waiting_list_data.append({
            'id': entry.id,
            'swimling_id': swimling.id,
            'swimling_name': f"{swimling.first_name} {swimling.last_name}",
            'is_transfer': entry.is_transfer_request,
            'has_enrolled_sibling': has_enrolled_sibling,

            'preference_1': entry.preferred_lesson_1 if entry.preferred_lesson_1 else None,
            'preference_2': entry.preferred_lesson_2 if entry.preferred_lesson_2 else None,
            'preference_3': entry.preferred_lesson_3 if entry.preferred_lesson_3 else None,

            'assigned_lesson': entry.assigned_lesson.name if entry.assigned_lesson else "Not assigned",
            'assigned_lesson_id': entry.assigned_lesson.id if entry.assigned_lesson else None,
            'can_book': entry.is_notified,
        })

    return waiting_list_data


def collect_previous_lessons(swimlings, current_term_id=None):
    """Return a mapping of swimling.id -> list of previous lesson summaries (newest first)."""
    history = defaultdict(list)
    swimlings = list(swimlings)
    if not swimlings:
        return history

    enrollments = (
        LessonEnrollment.objects
        .filter(swimling__in=swimlings)
        .select_related("lesson__category", "term")
        .order_by("-term__start_date", "-term__id", "-created")
    )
    if current_term_id:
        enrollments = enrollments.exclude(term_id=current_term_id)

    day_display_cache = {}
    for enrollment in enrollments:
        lesson = getattr(enrollment, "lesson", None)
        term = getattr(enrollment, "term", None)
        if not lesson or not term:
            continue

        category = getattr(lesson, "category", None)
        level = (
            getattr(category, "short_name", None)
            or getattr(category, "name", None)
            or getattr(lesson, "name", "")
        )

        day_key = getattr(lesson, "day_of_week", None)
        if day_key in day_display_cache:
            day_display = day_display_cache[day_key]
        else:
            try:
                day_display = lesson.get_day_of_week_display()
            except Exception:
                day_display = ""
            day_display_cache[day_key] = day_display

        start_time = getattr(lesson, "start_time", None)
        end_time = getattr(lesson, "end_time", None)
        time_parts = []
        if start_time:
            time_parts.append(start_time.strftime("%H:%M"))
        if end_time:
            time_parts.append(end_time.strftime("%H:%M"))
        time_label = " - ".join(time_parts)

        history[enrollment.swimling_id].append({
            "level": level,
            "day": day_display,
            "time": time_label,
            "term": getattr(term, "label", str(term)),
        })

    return history
