from django.shortcuts import render, redirect
from formtools.wizard.views import SessionWizardView
from .forms import UserRegistrationForm, SwimlingRegistrationForm, AddAnotherSwimlingForm
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from users.models import Swimling

User = get_user_model()


# Function to check if the user wants to add another swimling
def want_to_add_another(wizard):
    cleaned_data = wizard.get_cleaned_data_for_step('add_another') or {}
    return cleaned_data.get('add_another', False)


# Registration Wizard View
class RegistrationWizardView(SessionWizardView):
    template_name = 'user_registration.html'

    form_list = [
        ('user', UserRegistrationForm),
        ('swimling', SwimlingRegistrationForm),
        ('add_another', AddAnotherSwimlingForm),
    ]

    condition_dict = {'swimling': want_to_add_another}

    def get_context_data(self, form, **kwargs):
        context = super().get_context_data(form=form, **kwargs)

        if self.steps.current == 'swimling' and form.is_valid():
            swimling_data = form.cleaned_data
            print("Swimling Form Data:", swimling_data)

            # Initialize the session key if not already present
            if 'swimlings' not in self.request.session:
                self.request.session['swimlings'] = []

            # Add the valid swimling data to the session
            self.request.session['swimlings'].append(swimling_data)
            self.request.session.modified = True  # Mark session as modified

        return context

    def done(self, form_list, **kwargs):
        user_form = form_list[0].cleaned_data
        user = User.objects.create_user(
            email=user_form['email'],
            password=user_form['password1'],
            first_name=user_form['first_name'],
            last_name=user_form['last_name'],
            mobile_phone=user_form['mobile_phone']
        )

        # Process all swimlings data stored in session
        swimlings_data = self.request.session.get('swimlings', [])
        print("Swimlings Data:", swimlings_data)

        for swimling_data in swimlings_data:
            Swimling.objects.create(
                guardian=user,
                first_name=swimling_data['first_name'],
                last_name=swimling_data['last_name'],
                # Include other fields as necessary
            )

        # Clear the swimlings data from the session after processing
        self.request.session.pop('swimlings', None)

        return HttpResponse("Registration complete")
