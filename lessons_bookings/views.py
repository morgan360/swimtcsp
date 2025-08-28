from django.shortcuts import render, redirect
from formtools.wizard.views import SessionWizardView
from .forms import UserRegistrationForm, SwimlingRegistrationForm, AddAnotherSwimlingForm
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from users.models import Swimling
from django.contrib import messages
from django import forms
from django.contrib.admin.views.decorators import staff_member_required
from django.db.models import Prefetch
from django.contrib.auth.models import Group
from .models import Term, LessonAssignment
from lessons.models import Product


User = get_user_model()


# Function to check if the user wants to add another swimling
def want_to_add_another(wizard, step):
    cleaned_data = wizard.get_cleaned_data_for_step(step) or {}
    return cleaned_data.get('add_another', False)


# Registration Wizard View
class RegistrationWizardView(SessionWizardView):
    template_name = 'user_registration.html'

    form_list = [
        ('user', UserRegistrationForm),
        ('swimling1', SwimlingRegistrationForm),
        ('add_another1', AddAnotherSwimlingForm),
        ('swimling2', SwimlingRegistrationForm),
        ('add_another2', AddAnotherSwimlingForm),
    ]

    condition_dict = {
        'swimling1': lambda wizard: True,  # First swimling always shown
        'add_another1': lambda wizard: True,  # Always show the first 'add another' form
        'swimling2': lambda wizard: want_to_add_another(wizard, 'add_another1'),
        'add_another2': lambda wizard: want_to_add_another(wizard, 'swimling2'),
        # ... and so on for additional swimlings and add_another forms ...
    }

    def process_step(self, form):
        current_step = self.steps.current
        if isinstance(form, SwimlingRegistrationForm) and form.is_valid():
            print(f'Processing {current_step}')
            swimling_data = form.cleaned_data

            # Initialize the session key if not already present
            if 'swimlings' not in self.storage.extra_data:
                self.storage.extra_data['swimlings'] = []

            # Add the valid swimling data to the session
            self.storage.extra_data['swimlings'].append(swimling_data)

        return super().process_step(form)

    def done(self, form_list, **kwargs):
        # Create the user
        user_form = form_list[0].cleaned_data
        user = User.objects.create_user(
            email=user_form['email'],
            password=user_form['password1'],
            first_name=user_form['first_name'],
            last_name=user_form['last_name'],
            mobile_phone=user_form['mobile_phone']
        )
        # Create Swimling(s)
        # guardian = self.request.user  # Assuming the guardian is the current user
        guardian = user
        print(guardian)
        # Process all swimlings data stored in session
        swimlings_data = self.storage.extra_data.get('swimlings', [])
        print(swimlings_data)
        for swimling_data in swimlings_data:
            Swimling.objects.create(
                guardian=guardian,
                first_name=swimling_data['first_name'],
                last_name=swimling_data['last_name'],
            )

        # Clear the swimlings data from the session after processing
        self.request.session.pop('swimlings', None)

        messages.success(self.request, "Registration complete. Please log in.")
        return redirect('/accounts/login/')


class LessonAssignmentForm(forms.Form):
    term = forms.ModelChoiceField(
        queryset=Term.objects.all().order_by('-start_date'),
        label="Term",
        widget=forms.Select(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
        })
    )
    instructor = forms.ModelChoiceField(
        queryset=User.objects.filter(groups__name="instructors").distinct().order_by('first_name','last_name','email'),
        label="Instructor",
        widget=forms.Select(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500"
        })
    )
    lessons = forms.ModelMultipleChoiceField(
        queryset=Product.objects.all().order_by('name'),
        required=False,
        label="Lessons",
        widget=forms.SelectMultiple(attrs={
            "class": "w-full px-4 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-green-500 min-h-[240px]"
        })
    )


@staff_member_required
def instructor_assignments(request):
    """Front-end tool to assign an instructor to many lessons for a selected term."""
    form = LessonAssignmentForm(request.POST or None)

    if request.method == "POST" and form.is_valid():
        term = form.cleaned_data['term']
        instructor = form.cleaned_data['instructor']
        lessons = form.cleaned_data['lessons']
        assignment, _ = LessonAssignment.objects.get_or_create(term=term, instructor=instructor)
        assignment.lessons.set(lessons)
        messages.success(request, "Instructor assignments updated.")

    # Pre-fill lessons if both term & instructor are selected
    if form.is_valid():
        term = form.cleaned_data.get('term')
        instructor = form.cleaned_data.get('instructor')
        if term and instructor:
            try:
                existing = LessonAssignment.objects.get(term=term, instructor=instructor)
                form.fields['lessons'].initial = list(existing.lessons.values_list('id', flat=True))
            except LessonAssignment.DoesNotExist:
                pass

    # Load existing assignments for display
    assignments = (
        LessonAssignment.objects
        .select_related('term', 'instructor')
        .prefetch_related('lessons')
        .order_by('-term__start_date', 'instructor__first_name', 'instructor__last_name')
    )

    return render(request, "instructor_assignments.html", {
        "form": form,
        "assignments": assignments,
    })
