from django.shortcuts import render, redirect
from django.urls import reverse
from .models import Swimling
from schools_bookings.models import ScoEnrollment
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import HttpResponse
from .forms import UserForm, UserProfileForm, NewSwimlingForm
from django.contrib.auth import get_user_model
from lessons_bookings.models import LessonEnrollment, Term
from django.template.loader import render_to_string
from django.shortcuts import get_object_or_404
from utils.context_processors import get_term_info
from utils.context_processors import term_status_for_active_schools
from . helpers import fetch_swimling_management_data, fetch_normal_lessons_data, fetch_school_lessons_data
# Get the custom user model
user = get_user_model()


####### NEW COMBINED VIEW FOR SWIM MGMT PANEL#########
@login_required
def combined_swimling_mgmt(request):
    current_term_id = Term.get_current_term_id()
    term_data = get_term_info(request)
    school_term_status = term_status_for_active_schools(request)

    # Fetch swimling data
    swimling_management_data = fetch_swimling_management_data(request.user)

    # Fetch normal lessons
    normal_lessons_data = fetch_normal_lessons_data(request.user, current_term_id)

    # Fetch school lessons
    school_lessons_data = fetch_school_lessons_data(request.user)

    context = {
        'swimling_management_data': swimling_management_data,
        'normal_lessons': normal_lessons_data,
        'school_lessons_data': school_lessons_data,
        'term_data': term_data  # Additional context data
    }

    return render(request, 'users/combined_swimling_mgmt.html', context)

######################

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
def edit_swimling(request, id):
    swimling = get_object_or_404(Swimling, id=id, guardian=request.user)  # Ensure the user is the guardian

    if request.method == 'POST':
        form = NewSwimlingForm(request.POST, instance=swimling)
        if form.is_valid():
            form.save()
            messages.success(request, 'Swimling updated successfully.')
            return redirect('users:combined_swimling_mgmt')  # Redirect to the list of swimlings or a confirmation page
    else:
        form = NewSwimlingForm(instance=swimling)

    return render(request, 'edit_swimling.html', {'form': form, 'swimling': swimling})

#  Add a new swimmer to users portfolio
def add_new_swimling(request):
    if request.method == 'POST':
        form = NewSwimlingForm(request.POST)
        if form.is_valid():
            new_swimling = form.save(commit=False)
            new_swimling.guardian = request.user
            new_swimling.save()

            # Fetch updated swimlings for the dropdown
            swimling_management_data = fetch_swimling_management_data(request.user)
            # success message
            messages.success(request, 'Swimling added successfully.')
            # Render the partial template for the dropdown
            rendered_html = render_to_string('users/partials/swimlings_table.html', {'swimling_management_data':swimling_management_data},
                                             request=request)

            # Respond with the rendered HTML for HTMX to swap
            return HttpResponse(rendered_html)
        else:
            if "HX-Request" in request.headers:
                # If form is invalid during an HTMX request, return the form with errors
                context = {'form': form}
                html = render_to_string('partials/new_swimling_form.html', context, request=request)
                return HttpResponse(html, status=400)
            else:
                # For non-HTMX, render the form with errors within the context of a full page
                return render(request, 'partials/new_swimling_form.html', {'form': form})

    else:
        form = NewSwimlingForm()
        return render(request, 'partials/new_swimling_form.html', {'form': form})



def load_new_swimling_form(request, product_slug):
    form = NewSwimlingForm()
    product = Product.objects.get(slug=product_slug)  # Retrieve the product based on the slug
    return render(request, 'partials/new_swimling_form.html', {'form': form, 'product': product})
