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
from .forms import PublicWaitingListForm
from urllib.parse import quote

User = get_user_model()


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
def join_waiting_list(request, swimling_id):
    swimling = get_object_or_404(Swimling, id=swimling_id, guardian=request.user)

    if request.method == 'POST':
        form = PublicWaitingListForm(request.POST, swimling=swimling)

        # ✅ Set swimling manually
        form.instance.swimling = swimling

        # ✅ Extract and assign product
        product_id = form.data.get('preferred_lesson_1')
        if product_id:
            try:
                form.instance.product = Product.objects.get(id=product_id)
            except Product.DoesNotExist:
                form.add_error('preferred_lesson_1', 'Invalid lesson selected')

        if form.is_valid():
            form.save()

            messages.success(request, "You're on the list! We'll holler if a spot opens up.")
            return redirect('swimling_dashboard:guardian_dashboard')
    else:
        form = PublicWaitingListForm(swimling=swimling)

    return render(request, 'waiting_list/join_waiting_list.html', {
        'form': form,
        'swimling': swimling,
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

def remove_waiting_list_entry(request, id):
    entry = get_object_or_404(WaitingList, id=id)
    if request.method == 'POST':
        entry.delete()
    return redirect('swimling_dashboard:guardian_dashboard')

@login_required
def redirect_to_swimling_waiting_list(request):
    swimlings = Swimling.objects.filter(guardian=request.user)
    if swimlings.count() == 1:
        return redirect('waiting_list:join_waiting_list', swimling_id=swimlings.first().id)
    return redirect('swimling_dashboard:guardian_dashboard')