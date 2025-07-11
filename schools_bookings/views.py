from django.shortcuts import render, redirect, get_object_or_404
from formtools.wizard.views import SessionWizardView
from .forms import UserRegistrationForm, SwimlingRegistrationForm, AddAnotherSwimlingForm
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from users.models import Swimling
from django.contrib import messages
from .forms import DirectOrderForm
from schools.models import ScoSchool
from schools_bookings.models import ScoTerm
from schools_orders.models import Order, OrderItem
from boipa.views import initiate_boipa_payment_session
User = get_user_model()


def book_lesson(request, swimling_id, term_id):
    import logging
    logger = logging.getLogger(__name__)
    logger.warning("🔥 BOOK_LESSON VIEW TRIGGERED 🔥")

    swimling = get_object_or_404(Swimling, id=swimling_id)
    term = get_object_or_404(ScoTerm, id=term_id)
    school = get_object_or_404(ScoSchool, sco_role_num=swimling.sco_role_num)

    lessons = ScoLessons.objects.filter(
        term=term,
        school=school
    ).order_by('day_of_week', 'start_time')
    print("=== DEBUG: school ===")
    print(f"{school.name} ({school.sco_role_num})")

    print("=== DEBUG: lessons count ===")
    print(f"Lessons count: {lessons.count()}")

    for lesson in lessons:
        print(f"Lesson: {lesson.name} – {lesson.school.name} ({lesson.school.sco_role_num})")
    if request.method == 'POST':
        form = DirectOrderForm(request.POST, lessons=lessons)
        if form.is_valid():
            lesson = form.cleaned_data['lesson']

            # ✅ Step 1: Create the order
            order = Order.objects.create(
                user=request.user,
                amount=lesson.price,
                paid=False,
                school=school
            )

            # ✅ Step 2: Create the order item
            OrderItem.objects.create(
                order=order,
                term=term,
                product=lesson,
                price=lesson.price,
                quantity=1,
                swimling=swimling
            )

            # ✅ Step 3: Redirect to BOIPA checkout
            order_ref = f"school_{order.id}"
            return initiate_boipa_payment_session(request, order_ref, order.amount)

    else:
        form = DirectOrderForm(lessons=lessons)

    return render(request, 'schools_bookings/direct_order.html', {
        'form': form,
        'swimling': swimling,
        'school': school,
    })



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
