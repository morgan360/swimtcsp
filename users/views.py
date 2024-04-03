from django.shortcuts import render, redirect
from django import forms
from .models import UserProfile, User, Swimling
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from allauth.account.views import EmailVerificationSentView
from django.http import HttpResponse
from .forms import UserForm, UserProfileForm, NewSwimlingForm
from django.contrib.auth import get_user_model
from lessons_bookings.models import LessonEnrollment, Term
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from utils.context_processors import get_term_info
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


@login_required
def edit_swimling(request, id):
    swimling = get_object_or_404(Swimling, id= id, guardian=request.user)  # Ensure the user is the guardian

    if request.method == 'POST':
        form = NewSwimlingForm(request.POST, instance=swimling)
        if form.is_valid():
            form.save()
            messages.success(request, 'Swimling updated successfully.')
            return redirect('users:view-swimlings')  # Redirect to the list of swimlings or a confirmation page
    else:
        form = NewSwimlingForm(instance=swimling)

    return render(request, 'edit_swimling.html', {'form': form, 'swimling': swimling})


@login_required
def add_new_swimling(request):
    term_data = get_term_info(request)
    # when form is subbmitted
    if request.method == 'POST':
        form = NewSwimlingForm(request.POST)
        if form.is_valid():
            new_swimling = form.save(commit=False)
            new_swimling.guardian = request.user
            new_swimling.save()
            print("saved new swimling")
            # Fetch updated swimlings for the dropdown
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
                if term_data['next_term_id'] is not None:
                    # Check for next term's enrollment for the same course
                    enrollments_next_term = LessonEnrollment.objects.filter(
                        swimling=swimling,
                        term_id=next_term_id,
                        lesson__in=[enrollment.lesson for enrollment in enrollments_current_term]
                    ).select_related('lesson')
                    # Determine if the swimling is registered for the next term for the same course
                    is_registered_for_next_term_same_course = enrollments_next_term.exists()

                # Get names of all lessons the swimling is registered for (assuming there could be more than one)
                lesson_names = [enrollment.lesson.name for enrollment in enrollments]

                # Append swimling and their registration status and registered lesson names to the list
                swimlings_data.append({
                    'swimling': swimling,
                    'is_registered_for_current_term': is_registered_for_current_term,
                    'is_registered_for_next_term_same_course': is_registered_for_next_term_same_course,
                    'registered_lessons': lesson_names  # List of lesson names
                })

            # success message
            messages.success(request, 'Swimling added successfully.')
            # Render the partial template for the dropdown
            rendered_html = render_to_string('users/partials/swimlings_table.html', {'swimlings': swimlings_data},
                                             request=request)

            # Respond with the rendered HTML for HTMX to swap
            return HttpResponse(rendered_html)
        # *** form not valid ***
        else:
            if "HX-Request" in request.headers:
                # If form is invalid during an HTMX request, return the form with errors
                context = {'form': form}
                html = render_to_string('partials/new_swimling_form.html', context, request=request)
                return HttpResponse(html, status=400)
            else:
                # For non-HTMX, render the form with errors within the context of a full page
                return render(request, 'partials/new_swimling_form.html', {'form': form})
    # If form not submitted
    else:
        form = NewSwimlingForm()
        return render(request, 'partials/new_swimling_form.html', {'form': form})
