from django.shortcuts import render, redirect, get_object_or_404
from formtools.wizard.views import SessionWizardView
from .forms import UserRegistrationForm, SwimlingRegistrationForm, AddAnotherSwimlingForm
from django.http import HttpResponse
from django.contrib.auth import get_user_model
from users.models import Swimling
from django.contrib import messages
from .forms import DirectOrderForm
from schools.models import ScoSchool,ScoLessons
from schools_bookings.models import ScoTerm
from schools_bookings.utils.swimling_utils import get_latest_active_school_term
from schools_orders.models import Order, OrderItem
from boipa.views import initiate_boipa_payment_session
from decimal import Decimal
from coupons.models import Coupon
from coupons.services import CouponService
from django.core.exceptions import ValidationError
import logging
import sys

User = get_user_model()




def book_lesson(request, swimling_id, term_id):
    logger = logging.getLogger(__name__)
    print("💡 book_lesson view STARTED", file=sys.stderr)

    swimling = get_object_or_404(Swimling, id=swimling_id)
    school = get_object_or_404(ScoSchool, sco_role_num=swimling.sco_role_num)

    # ✅ Get the active term for this school (not current term - allows advance booking)
    term = get_latest_active_school_term(swimling.sco_role_num)
    if not term:
        return HttpResponse("No active term available for this school.", status=400)

    lessons = ScoLessons.objects.filter(
        school=school
    ).order_by('day_of_week', 'start_time')

    if request.method == 'POST':
        form = DirectOrderForm(request.POST, lessons=lessons)
        print("📥 POST received", file=sys.stderr)

        if not form.is_valid():
            print("❌ FORM INVALID", file=sys.stderr)
            print(form.errors.as_json(), file=sys.stderr)
        else:
            print("✅ FORM VALID", file=sys.stderr)
            lesson = form.cleaned_data['lesson']

            # Create base order
            order = Order.objects.create(
                user=request.user,
                amount=lesson.price,
                paid=False,
                school=school
            )

            # Handle coupon logic
            coupon_code = request.POST.get('code', '').strip()
            discount = Decimal("0.00")
            coupon = None

            if coupon_code:
                try:
                    coupon = Coupon.objects.get(code=coupon_code)
                    service = CouponService(coupon)
                    discount = service.apply(
                        purchase_obj=order,
                        amount=lesson.price,
                        user=request.user
                    )
                    print(f"✅ Coupon applied: {coupon.code}, discount: €{discount}", file=sys.stderr)
                except (Coupon.DoesNotExist, ValidationError) as e:
                    print(f"[Coupon Error] {e}", file=sys.stderr)

            # Update order with final values
            order.amount = lesson.price - discount
            order.discount_amount = discount
            order.coupon = coupon
            order.save()

            # Create order item
            OrderItem.objects.create(
                order=order,
                term=term,
                product=lesson,
                price=lesson.price,
                quantity=1,
                swimling=swimling
            )

            # Log final details
            print(f"FINAL ORDER ID: {order.id}", file=sys.stderr)
            print(f"FINAL AMOUNT: €{order.amount}", file=sys.stderr)
            print(f"DISCOUNT AMOUNT: €{order.discount_amount}", file=sys.stderr)
            print(f"COUPON USED: {order.coupon.code if order.coupon else 'None'}", file=sys.stderr)

            order_ref = f"school_{order.id}"
            return initiate_boipa_payment_session(request, order_ref, order.amount)

    else:
        form = DirectOrderForm(lessons=lessons)

    return render(request, 'schools_bookings/direct_order.html', {
        'form': form,
        'swimling': swimling,
        'school': school,
        'term': term,
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
