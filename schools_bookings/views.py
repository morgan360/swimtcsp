from django.shortcuts import render, redirect
from formtools.wizard.views import SessionWizardView
from .forms import UserRegistrationForm, SwimlingRegistrationForm, AddAnotherSwimlingForm
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from users.models import Swimling
from django.contrib import messages


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
