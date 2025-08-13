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
            messages.success(request, "Congratulations! You are now a Guardian and can access all lesson booking features.")
            
            # Check if user came from a specific URL and redirect there
            from_url = request.GET.get('from')
            if from_url:
                return redirect(from_url)
            return redirect('/')  # Default redirect to home
    else:
        form = GuardianOptInForm()

    return render(request, 'users/become_guardian.html', {
        'form': form,
        'from_url': request.GET.get('from', ''),
    })

# ✅ Schools Opt-in View
@login_required
def join_schools_program(request):
    if request.method == 'POST':
        form = JoinSchoolsForm(request.POST)
        if form.is_valid():
            schools_group, _ = Group.objects.get_or_create(name='schools')
            request.user.groups.add(schools_group)
            return redirect("swimling_dashboard")  # or wherever you want to redirect
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
