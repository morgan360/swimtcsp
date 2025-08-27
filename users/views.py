from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .forms import UserForm, GuardianOptInForm, JoinSchoolsForm
from django.shortcuts import render, redirect
from allauth.account.views import SignupView
from schools_bookings.utils.swimling_utils import get_latest_active_school_term
from schools_bookings.models import ScoEnrollment
from utils.context_processors import get_term_info
from lessons.models import Product
from schools_bookings.models import ScoEnrollment

# Get the custom user model
user = get_user_model()

# ✅ User Profile Update View
@login_required
@transaction.atomic
def update_profile(request):
    # Check if user was redirected here for guardian access
    guardian_required = request.GET.get('guardian_required') == 'true'
    from_url = request.GET.get('from', '')
    
    # Check if user is already a guardian
    is_guardian = request.user.groups.filter(name='guardian').exists()
    
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        if user_form.is_valid():
            user_form.save()
            messages.success(request, "Your profile has been updated.")
            return redirect("home")
    else:
        user_form = UserForm(instance=request.user)

    return render(request, "profile.html", {
        "u_form": user_form,
        "guardian_required": guardian_required,
        "from_url": from_url,
        "is_guardian": is_guardian,
    })


# ✅ Hijack Redirection After Admin Login-as
def hijack_redirect(request, user_id):
    user_first_name = request.user.first_name
    user_last_name = request.user.last_name
    fullname = f"{user_first_name} {user_last_name}"
    messages.success(request, f"You are now logged in as {fullname}.")
    return redirect('home')


# ✅ Guardian Opt-in View
@login_required
def become_guardian_view(request):
    if request.method == 'POST':
        form = GuardianOptInForm(request.POST)
        if form.is_valid() and form.cleaned_data['become_guardian']:
            guardian_group, _ = Group.objects.get_or_create(name='guardian')
            request.user.groups.add(guardian_group)
            messages.success(request, "Congratulations! You are now a Guardian and can access the Swimling Dashboard.")
            
            # Check for redirect destination
            redirect_to = request.POST.get('redirect_to')
            from_url = request.GET.get('from')
            
            # Priority: redirect_to field > from_url > swimling dashboard default
            if redirect_to == 'swimling_dashboard':
                return redirect('swimling_dashboard:guardian_dashboard')
            elif from_url:
                return redirect(from_url)
            else:
                return redirect('swimling_dashboard:guardian_dashboard')  # Default to dashboard
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
    user_in_school_group = request.user.groups.filter(name='school').exists()
    
    if user_in_school_group:
        messages.info(request, "You already have access to the School Swimming Program!")
        return redirect('swimling_dashboard:guardian_dashboard')
    
    if request.method == 'POST':
        form = JoinSchoolsForm(request.POST)
        if form.is_valid():
            school_group, _ = Group.objects.get_or_create(name='school')
            request.user.groups.add(school_group)
            messages.success(request, "Welcome to the School Swimming Program!")
            return redirect('swimling_dashboard:guardian_dashboard')
    else:
        form = JoinSchoolsForm()

    return render(request, "users/join_schools.html", {"form": form})


class CustomSignupView(SignupView):
    def dispatch(self, request, *args, **kwargs):
        print("🚨 CustomSignupView dispatch triggered")
        if request.user.is_authenticated:
            list(messages.get_messages(request))  # reads + clears the queue
            messages.info(request, "You are already logged in.")
            return redirect("swimling_dashboard:guardian_dashboard")  # or another named view like 'dashboard'
        return super().dispatch(request, *args, **kwargs)

from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Q
from django.core.paginator import Paginator
from .models import Swimling


@staff_member_required
def swimlings_list(request):
    """Dashboard-facing view to browse and manage swimlings (search, paginate) and show current classes (public + school)."""
    search = request.GET.get("search", "").strip()

    qs = (
        Swimling.objects
        .select_related("guardian")
        .order_by("first_name", "last_name")
    )

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search)
            | Q(last_name__icontains=search)
            | Q(guardian__email__icontains=search)
            | Q(guardian__first_name__icontains=search)
            | Q(guardian__last_name__icontains=search)
        )

    paginator = Paginator(qs, 25)  # 25 per page
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    # === Build current classes per swimling (Public + School) ===
    # Public: use current public term from context processor
    term_info = get_term_info(request)
    current_term_id = term_info.get("current_term_id")

    public_by_swimling = {}
    if current_term_id:
        public_rows = (
            Product.objects
            .filter(
                enrollments__term_id=current_term_id,
                enrollments__swimling__in=page_obj.object_list,
            )
            .values("enrollments__swimling_id", "name")
        )
        for r in public_rows:
            public_by_swimling.setdefault(r["enrollments__swimling_id"], []).append(r["name"])

    # Attach combined classes to each swimling on the current page
    for s in page_obj.object_list:
        classes = list(public_by_swimling.get(s.id, []))
        # School: use latest active school term for this swimling (if any)
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
                        classes.append(se.lesson.name)
        setattr(s, "current_classes", classes)

    context = {
        "search": search,
        "page_obj": page_obj,
        "swimlings": page_obj.object_list,
        "total": paginator.count,
    }
    return render(request, "users/swimlings_list.html", context)
