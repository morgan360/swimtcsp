from collections import defaultdict
from datetime import date
import logging

from allauth.account.views import SignupView
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, Value
from django.db.models.functions import Concat, Coalesce
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone

from schools_bookings.models import ScoEnrollment
from schools_bookings.utils.swimling_utils import get_latest_active_school_term
from utils.context_processors import get_term_info
from lessons_bookings.models import LessonEnrollment
from lessons_orders.models import Order as LessonOrder
from swims_orders.models import Order as SwimOrder
from schools_orders.models import Order as SchoolOrder
from users.helpers import collect_previous_lessons
from users.utils.roles import is_guardian
from .forms import UserForm, GuardianOptInForm, JoinSchoolsForm
from .models import Swimling


# Get the custom user model
user = get_user_model()
logger = logging.getLogger(__name__)


def build_current_public_classes(swimlings, term_info):
    """Return swimling_id -> list of active or upcoming public classes."""
    swimlings = list(swimlings)
    if not swimlings:
        return {}

    today = timezone.localdate()
    current_term_id = term_info.get("current_term_id")
    next_term_id = term_info.get("next_term_id")

    buckets = defaultdict(lambda: {"active": {}, "future": {}})
    enrollments = (
        LessonEnrollment.objects
        .filter(swimling__in=swimlings)
        .select_related("lesson", "term")
    )

    for enrollment in enrollments:
        term = getattr(enrollment, "term", None)
        lesson = getattr(enrollment, "lesson", None)
        if not term or not lesson:
            continue

        start = term.start_date
        end = term.end_date
        bucket = None
        if start and end:
            if start <= today <= end:
                bucket = "active"
            elif start > today:
                bucket = "future"
        elif current_term_id and term.id == current_term_id:
            bucket = "active"
        elif next_term_id and term.id == next_term_id:
            bucket = "future"
        if bucket is None:
            if not start and not end and not current_term_id:
                bucket = "active"
            else:
                continue

        entry = buckets[enrollment.swimling_id][bucket].setdefault(
            term.id,
            {"term": term, "enrollments": []},
        )
        entry["enrollments"].append(enrollment)

    public_map = {}
    for swimling in swimlings:
        data = buckets.get(swimling.id)
        if not data:
            continue

        selected_terms = []
        if data["active"]:
            selected_terms = sorted(
                data["active"].items(),
                key=lambda item: (
                    item[1]["term"].start_date or date.max,
                    item[0],
                ),
            )
        elif data["future"]:
            future_terms = sorted(
                data["future"].items(),
                key=lambda item: (
                    item[1]["term"].start_date or date.max,
                    item[0],
                ),
            )
            if future_terms:
                selected_terms = [future_terms[0]]

        classes = []
        for _, entry in selected_terms:
            for enrollment in entry["enrollments"]:
                lesson = enrollment.lesson
                if not lesson:
                    continue
                try:
                    admin_url = reverse(
                        "lessonsadmin:lessons_bookings_lessonenrollment_change",
                        args=[enrollment.id],
                    )
                except Exception:
                    admin_url = (
                        f"/lessonsadmin/lessons_bookings/lessonenrollment/{enrollment.id}/change/"
                    )
                classes.append({
                    "name": lesson.name or "",
                    "enrollment_id": enrollment.id,
                    "admin_url": admin_url,
                })

        if classes:
            public_map[swimling.id] = classes

    return public_map


# ✅ User Profile Update View
@login_required
@transaction.atomic
def update_profile(request):
    guardian_required = request.GET.get('guardian_required') == 'true'
    from_url = request.GET.get('from', '')
    is_guardian_flag = is_guardian(request.user)
    user_in_school_group = request.user.groups.filter(name__in=['school', 'Schools']).exists()

    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Your profile has been updated.")
            # Stay on profile after successful update
            return redirect("users:profile")
    else:
        user_form = UserForm(instance=request.user)

    return render(request, "profile.html", {
        "u_form": user_form,
        "guardian_required": guardian_required,
        "from_url": from_url,
        "is_guardian": is_guardian_flag,
        "user_in_school_group": user_in_school_group,
    })


# ✅ Hijack Redirection After Admin Login-as
def hijack_redirect(request, user_id):
    user_first_name = request.user.first_name
    user_last_name = request.user.last_name
    fullname = f"{user_first_name} {user_last_name}"
    messages.success(request, f"You are now logged in as {fullname}.")
    return redirect('home')


@login_required
def become_guardian_view(request):
    if request.method == 'POST':
        form = GuardianOptInForm(request.POST)
        if form.is_valid() and form.cleaned_data['become_guardian']:
            # Check if user is already in either group
            if not is_guardian(request.user):
                guardian_group, _ = Group.objects.get_or_create(name='guardian')
                request.user.groups.add(guardian_group)
                messages.success(request, "Congratulations! You are now a Guardian and can access the Swimling Dashboard.")
            else:
                messages.info(request, "You are already a Guardian and can access the Swimling Dashboard.")
            
            # Check for redirect destination
            redirect_to = request.POST.get('redirect_to')
            from_url = request.GET.get('from')
            
            # Priority: redirect_to field > from_url > swimling dashboard default
            if redirect_to == 'swimling_dashboard':
                return redirect('swimling_dashboard:guardian_dashboard')
            elif from_url:
                return redirect(from_url)
            else:
                return redirect('swimling_dashboard:guardian_dashboard')
    else:
        form = GuardianOptInForm()

    return render(request, 'users/become_guardian.html', {
        'form': form,
        'from_url': request.GET.get('from', ''),
    })


# ✅ Schools Opt-in View
@login_required
def join_schools_program(request):
    # Check if user already has school access
    user_in_school_group = request.user.groups.filter(name__in=['school', 'Schools']).exists()

    if user_in_school_group:
        messages.info(request, "You already have access to the School Swimming Program!")
        return redirect('swimling_dashboard:guardian_dashboard')
    
    if request.method == 'POST':
        form = JoinSchoolsForm(request.POST)
        if form.is_valid():
            school_group, _ = Group.objects.get_or_create(name='Schools')
            request.user.groups.add(school_group)
            messages.success(request, "Welcome to the School Swimming Program!")
            return redirect('swimling_dashboard:guardian_dashboard')
    else:
        form = JoinSchoolsForm()

    return render(request, "users/join_schools.html", {"form": form})


class CustomSignupView(SignupView):
    def dispatch(self, request, *args, **kwargs):
        if request.user.is_authenticated:
            list(messages.get_messages(request))  # reads + clears the queue
            messages.info(request, "You are already logged in.")
            # Role-aware redirect: Guardians → dashboard; others → profile
            if is_guardian(request.user):
                return redirect("swimling_dashboard:guardian_dashboard")
            return redirect('')
        return super().dispatch(request, *args, **kwargs)


# Post-login router used by Get Started button
@login_required
def after_login(request):
    """Redirect guardians to dashboard; others to profile."""
    if is_guardian(request.user):
        return redirect('swimling_dashboard:guardian_dashboard')
    return redirect('users:profile')


@staff_member_required
def swimlings_list(request):
    """Dashboard-facing view to browse and manage swimlings (search, paginate) and show current classes (public + school) with per-enrollment Move links."""
    search = request.GET.get("search", "").strip()

    qs = (
        Swimling.objects
        .select_related("guardian")
        .annotate(
            full_name=Concat(
                Coalesce("first_name", Value("")),
                Value(" "),
                Coalesce("last_name", Value("")),
            ),
            guardian_full_name=Concat(
                Coalesce("guardian__first_name", Value("")),
                Value(" "),
                Coalesce("guardian__last_name", Value("")),
            ),
        )
        .order_by("first_name", "last_name")
    )

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(guardian__email__icontains=search)
            | Q(guardian__first_name__icontains=search)
            | Q(guardian__last_name__icontains=search)
            | Q(full_name__icontains=search)
            | Q(guardian_full_name__icontains=search)
        )

    paginator = Paginator(qs, 25)  # 25 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # === Build current classes per swimling (Public + School) ===
    term_info = get_term_info(request)
    current_term_id = term_info.get("current_term_id")
    public_by_swimling = build_current_public_classes(page_obj.object_list, term_info)

    # Attach combined classes to each swimling on the current page
    for s in page_obj.object_list:
        classes = list(public_by_swimling.get(s.id, []))
        # School: use latest active school term for this swimling
        try:
            if getattr(s, "sco_role_num", None):
                st = get_latest_active_school_term(s.sco_role_num)
                if st:
                    school_qs = (
                        ScoEnrollment.objects
                        .filter(swimling=s, term=st)
                        .select_related("lesson")
                    )
                    for se in school_qs:
                        if getattr(se, "lesson", None) and getattr(se.lesson, "name", None):
                            try:
                                se_admin_url = reverse("schoolsadmin:schools_bookings_scoenrollment_change", args=[se.id])
                            except Exception:
                                se_admin_url = f"/schoolsadmin/schools_bookings/scoenrollment/{se.id}/change/"
                            classes.append({
                                "name": se.lesson.name,
                                "enrollment_id": se.id,
                                "admin_url": se_admin_url,
                            })
        except Exception:
            logger.exception("swimlings_list: failed building school enrollments for swimling=%s", getattr(s, 'id', '?'))
        # Optional: dedupe by name while preserving order (handles duplicate same-named classes)
        seen = set()
        deduped = []
        for item in classes:
            nm = item.get("name")
            key = (nm, item.get("enrollment_id"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        setattr(s, "current_classes", deduped)

    history_map = collect_previous_lessons(page_obj.object_list, current_term_id)
    for s in page_obj.object_list:
        setattr(s, "previous_terms", history_map.get(s.id, []))

    context = {
        "search": search,
        "page_obj": page_obj,
        "swimlings": page_obj.object_list,
        "total": paginator.count,
    }
    return render(request, "users/swimlings_list.html", context)


@staff_member_required
def swimlings_list_rows(request):
    """Returns paginated markup for Swimlings to support infinite scroll.
    Pass `variant=desktop|mobile` to choose rows vs cards.
    """
    search = request.GET.get("search", "").strip()
    page_number = request.GET.get("page")

    qs = (
        Swimling.objects
        .select_related("guardian")
        .annotate(
            full_name=Concat(
                Coalesce("first_name", Value("")),
                Value(" "),
                Coalesce("last_name", Value("")),
            ),
            guardian_full_name=Concat(
                Coalesce("guardian__first_name", Value("")),
                Value(" "),
                Coalesce("guardian__last_name", Value("")),
            ),
        )
        .order_by("first_name", "last_name")
    )

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(guardian__email__icontains=search)
            | Q(guardian__first_name__icontains=search)
            | Q(guardian__last_name__icontains=search)
            | Q(full_name__icontains=search)
            | Q(guardian_full_name__icontains=search)
        )

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(page_number)

    # Build current classes like the main view
    term_info = get_term_info(request)
    current_term_id = term_info.get("current_term_id")
    public_by_swimling = build_current_public_classes(page_obj.object_list, term_info)

    for s in page_obj.object_list:
        classes = list(public_by_swimling.get(s.id, []))
        try:
            if getattr(s, "sco_role_num", None):
                st = get_latest_active_school_term(s.sco_role_num)
                if st:
                    school_qs = (
                        ScoEnrollment.objects
                        .filter(swimling=s, term=st)
                        .select_related("lesson")
                    )
                    for se in school_qs:
                        if getattr(se, "lesson", None) and getattr(se.lesson, "name", None):
                            try:
                                se_admin_url = reverse("schoolsadmin:schools_bookings_scoenrollment_change", args=[se.id])
                            except Exception:
                                se_admin_url = f"/schoolsadmin/schools_bookings/scoenrollment/{se.id}/change/"
                            classes.append({
                                "name": se.lesson.name,
                                "enrollment_id": se.id,
                                "admin_url": se_admin_url,
                            })
        except Exception:
            logger.exception("swimlings_list_rows: failed building school enrollments for swimling=%s", getattr(s, 'id', '?'))
        seen = set()
        deduped = []
        for item in classes:
            nm = item.get("name")
            key = (nm, item.get("enrollment_id"))
            if key in seen:
                continue
            seen.add(key)
            deduped.append(item)
        setattr(s, "current_classes", deduped)

    history_map = collect_previous_lessons(page_obj.object_list, current_term_id)
    for s in page_obj.object_list:
        setattr(s, "previous_terms", history_map.get(s.id, []))

    variant = request.GET.get('variant', 'desktop')
    template_name = 'users/_swimling_rows.html' if variant == 'desktop' else 'users/_swimling_cards.html'
    html = render(request, template_name, {
        'swimlings': page_obj.object_list,
    }).content.decode('utf-8')

    data = {
        'html': html,
        'next_page': page_obj.next_page_number() if page_obj.has_next() else None,
        'count_this_page': len(page_obj.object_list),
    }
    return JsonResponse(data)


# =============================
# My Bookings (Lessons + Swims)
# =============================
@login_required
def my_bookings(request):
    # Lessons: group by order to show coupon/discount breakdown
    lesson_orders_base = (
        LessonOrder.objects
        .filter(user=request.user)
        .prefetch_related('items__product', 'items__term', 'items__swimling')
        .select_related('coupon')
        .order_by('-created')
    )
    lesson_orders_paid = lesson_orders_base.filter(paid=True)
    lesson_orders_unpaid = lesson_orders_base.filter(paid=False)

    # Public Swims: orders with items and product/variants
    swim_orders_base = (
        SwimOrder.objects
        .filter(user=request.user)
        .select_related('product', 'coupon')
        .prefetch_related('items__variant')
        .order_by('-created')
    )
    swim_orders_paid = swim_orders_base.filter(paid=True)
    swim_orders_unpaid = swim_orders_base.filter(paid=False)

    school_orders_base = (
        SchoolOrder.objects
        .filter(user=request.user)
        .select_related('school', 'coupon')
        .prefetch_related('items__product', 'items__term', 'items__swimling')
        .order_by('-created')
    )
    school_orders_paid = school_orders_base.filter(paid=True)
    school_orders_unpaid = school_orders_base.filter(paid=False)

    return render(request, 'users/my_bookings.html', {
        'lesson_orders_paid': lesson_orders_paid,
        'lesson_orders_unpaid': lesson_orders_unpaid,
        'swim_orders_paid': swim_orders_paid,
        'swim_orders_unpaid': swim_orders_unpaid,
        'school_orders_paid': school_orders_paid,
        'school_orders_unpaid': school_orders_unpaid,
    })
