from django.shortcuts import render, redirect
from django import forms
from .models import UserProfile, User, Swimling
from django.contrib.auth.models import User
from django.db import transaction
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from allauth.account.views import EmailVerificationSentView
from django.http import HttpResponse


# from .forms import SwimlingForm


class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name")


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('notes_extra',)


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
            return redirect("user:profile")
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

# To save Swimling

# def add_swimling(request):
#     if request.method == "POST":
#         form = SwimlingForm(request.POST)
#         if form.is_valid():
#             form.save()  # Save the Swimling instance to the database
#             return redirect(
#                 "success_url")  # Replace "success_url" with the URL you want to redirect to after successful form submission
#     else:
#         form = SwimlingForm()
#     return render(request, "your_template.html", {"form": form})

# views.py
