from django.shortcuts import render, redirect
from django import forms
from .models import UserProfile, User, Swimling
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from allauth.account.views import EmailVerificationSentView
from django.http import HttpResponse
from .forms import UserForm, UserProfileForm
from django.contrib.auth import get_user_model

# Get the custom user model
user = get_user_model()


@login_required
@transaction.atomic
def update_profile(request):
    if request.method == "POST":
        user_form = UserForm(request.POST, instance=request.user)
        user_profile_form = UserProfileForm(request.POST,
                                            instance=request.user.userprofile)
        if user_form.is_valid() and user_profile_form.is_valid():
            user_form.save()
            user_profile_form.save()
            messages.success(request, "Saved")
            return redirect("home")
    else:
        user_form = UserForm(instance=request.user)
        user_profile_form = UserProfileForm(instance=request.user.userprofile)
    return render(request, "profile.html",
                  {"u_form": user_form, "p_form": user_profile_form})


def hijack_redirect(request, user_id):
    user_id_value = int(user_id)
    user_first_name = request.user.first_name
    user_last_name = request.user.last_name

    fullname = f"{user_first_name} {user_last_name}"
    # Assuming your custom User model has a 'username' field
    # user_name = User.objects.get(id=user_id_value).username

    # Display a message
    messages.success(request, f"You are now logged in as {fullname}.")

    # Redirect to the home page or any other desired URL
    return redirect('home')  # Replace 'home' with the name of your home page URL pattern


@login_required
def view_swimlings(request):
    # Query for swimlings associated with the currently logged-in user's guardian field
    swimlings = Swimling.objects.filter(guardian=request.user)

    return render(request, 'swimling_list.html', {'swimlings': swimlings})
