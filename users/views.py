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
from lessons_bookings.models import LessonEnrollment, Term

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
    # Get the ID of the current term
    current_term_id = Term.get_current_term_id()

    # Query for swimlings associated with the currently logged-in user's guardian field
    swimlings = Swimling.objects.filter(guardian=request.user)

    # Prepare swimlings data including lesson registration status and lesson name for the current term
    swimlings_data = []
    for swimling in swimlings:
        # Fetch lesson enrollments for the swimling in the current term
        enrollments = LessonEnrollment.objects.filter(
            swimling=swimling,
            term_id=current_term_id
        ).select_related('lesson')  # Ensure related lesson data is fetched efficiently

        # Check if the swimling is registered for any lessons in the current term
        is_registered_for_current_term = enrollments.exists()

        # Get names of all lessons the swimling is registered for (assuming there could be more than one)
        lesson_names = [enrollment.lesson.name for enrollment in enrollments]

        # Append swimling and their registration status and registered lesson names to the list
        swimlings_data.append({
            'swimling': swimling,
            'is_registered_for_current_term': is_registered_for_current_term,
            'registered_lessons': lesson_names  # List of lesson names
        })

    return render(request, 'swimling_list.html', {'swimlings': swimlings_data})


