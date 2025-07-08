from django.shortcuts import render, redirect
from django.urls import reverse
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from .forms import UserForm, UserProfileForm, GuardianOptInForm

# Get the custom user model
user = get_user_model()

# ✅ User Profile Update View
@login_required
@transaction.atomic
def update_profile(request):
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        user_profile_form = UserProfileForm(
            request.POST,
            instance=request.user.userprofile
        )
        if user_form.is_valid() and user_profile_form.is_valid():
            user_form.save()
            user_profile_form.save()
            messages.success(request, "Saved")
            return redirect("home")
    else:
        user_form = UserForm(instance=request.user)
        user_profile_form = UserProfileForm(instance=request.user.userprofile)

    return render(request, "profile.html", {
        "u_form": user_form,
        "p_form": user_profile_form
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
            return redirect('/')  # Or any success page
    else:
        form = GuardianOptInForm()

    return render(request, 'users/become_guardian.html', {'form': form})
