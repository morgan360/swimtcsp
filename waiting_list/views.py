from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import WaitingList
from lessons.models import Product
from users.models import Swimling
from django.shortcuts import get_object_or_404, redirect, render
from django.contrib import messages

import secrets
from django.contrib.auth import login
from django.core.mail import send_mail
from .forms import PublicWaitingListForm
from users.models import Swimling
from .models import WaitingList
from django.conf import settings
from django.urls import reverse

from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import get_user_model
from django import forms
from django.contrib import messages

from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse
from django.contrib.auth import get_user_model
from .forms import EmailOnlyForm, PublicWaitingListForm
from urllib.parse import quote

User = get_user_model()


def enter_email_for_waiting_list(request):
    if request.method == 'POST':
        form = EmailOnlyForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']

            if not request.user.is_authenticated and User.objects.filter(email=email).exists():
                messages.info(
                    request,
                    "You already have an account. Please log in to continue your waiting list application."
                )
                next_url = f"{reverse('waiting_list:public_signup')}?email={email}"
                encoded_next = quote(next_url)
                login_url = reverse('account_login')
                return redirect(f"{login_url}?next={encoded_next}")

            # Otherwise: go to step 2 of the form
            return redirect(f"{reverse('waiting_list:public_signup')}?email={email}")
    else:
        form = EmailOnlyForm()

    return render(request, 'waiting_list/enter_email.html', {'form': form})


def public_waiting_list_signup(request):
    guardian = request.user if request.user.is_authenticated else None

    initial_email = request.GET.get('email') or request.POST.get('email')

    if request.method == 'POST':
        form = PublicWaitingListForm(request.POST, guardian=guardian)
        if form.is_valid():
            email = form.cleaned_data['email']
            full_name = form.cleaned_data['full_name']
            is_transfer = form.cleaned_data['is_transfer_request'] == 'True'

            preferred_1 = form.cleaned_data['preferred_lesson_1']
            preferred_2 = form.cleaned_data['preferred_lesson_2']
            preferred_3 = form.cleaned_data['preferred_lesson_3']

            if not guardian:
                guardian = User.objects.filter(email=email).first()
                if not guardian:
                    password = secrets.token_urlsafe(10)
                    guardian = User.objects.create_user(
                        username=email, email=email, password=password, first_name=full_name
                    )
                    send_mail(
                        subject="Welcome to Swim Waiting List",
                        message=f"Hi {full_name},\n\nWe’ve created an account for you using this email.",
                        from_email=settings.DEFAULT_FROM_EMAIL,
                        recipient_list=[email],
                    )
                    login(request, guardian)

            swimling = form.cleaned_data.get('swimling')
            if not swimling:
                swimling = Swimling.objects.create(
                    name=form.cleaned_data['swimling_name'],
                    date_of_birth=form.cleaned_data['swimling_dob'],
                    guardian=guardian
                )

            WaitingList.objects.create(
                swimling=swimling,
                product=preferred_1,
                is_transfer_request=is_transfer,
                preferred_lesson_1=preferred_1,
                preferred_lesson_2=preferred_2,
                preferred_lesson_3=preferred_3,
            )

            return redirect('waiting_list:waiting_list_success')

    else:
        form = PublicWaitingListForm(guardian=guardian, initial={'email': initial_email})

    return render(request, 'waiting_list/public_signup.html', {'form': form})

@login_required
def join_waiting_list(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    swimlings = Swimling.objects.filter(guardian=request.user)  # Assuming Swimling has a guardian field

    if request.method == 'POST':
        swimling_id = request.POST.get('swimling')
        swimling = get_object_or_404(Swimling, id=swimling_id)

        WaitingList.objects.create(
            swimling=swimling,
            product=product,
        )
        return redirect('waiting_list:waiting_list_success')  # You can create this view/template for a success message

    return render(request, 'waiting_list/join_waiting_list.html', {
        'swimlings': swimlings,
        'product': product,
    })


@staff_member_required
def manage_waiting_list(request):
    waiting_list = WaitingList.objects.filter(is_notified=False)

    if request.method == 'POST':
        waiting_list_id = request.POST.get('waiting_list_id')
        lesson_id = request.POST.get('lesson_id')
        waiting_entry = get_object_or_404(WaitingList, id=waiting_list_id)
        lesson = get_object_or_404(Product, id=lesson_id)

        waiting_entry.assigned_lesson = lesson
        waiting_entry.is_notified = True
        waiting_entry.save()

        # Notify the customer
        # send_waiting_list_notification(
        #     waiting_entry.user.email,
        #     waiting_entry.swimling.name,
        #     lesson.name
        # )

        messages.success(request, 'Customer has been notified and assigned to the lesson.')

    return render(request, 'waiting_list/manage_waiting_list.html', {
        'waiting_list': waiting_list,
    })


@staff_member_required
def notify_customer(request, waiting_list_id):
    waiting_entry = get_object_or_404(WaitingList, id=waiting_list_id)
    waiting_entry.is_notified = True
    waiting_entry.notification_date = timezone.now()
    waiting_entry.save()
    # send_waiting_list_notification(waiting_entry.user.email, waiting_entry.swimling.name, waiting_entry.product.name)
    return redirect('manage_waiting_list')


def waiting_list_success(request):
    return render(request, 'waiting_list/success.html')

def remove_waiting_list_entry(request, id):
    entry = get_object_or_404(WaitingList, id=id)
    if request.method == 'POST':
        entry.delete()
    return redirect('swimling_dashboard:guardian_dashboard')