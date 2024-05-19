from django.shortcuts import get_object_or_404, redirect, render
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.utils import timezone
from .models import WaitingList
from lessons.models import Product
from users.models import Swimling
from .utils import send_waiting_list_notification  # Assuming you put the email sending function in a utils module


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
            user=request.user
        )
        return redirect('waiting_list:waiting_list_success')  # You can create this view/template for a success message

    return render(request, 'waiting_list/join_waiting_list.html', {
        'swimlings': swimlings,
        'product': product,
    })


from django.shortcuts import get_object_or_404, redirect, render
from .models import WaitingList
from lessons.models import Product
from .utils import send_waiting_list_notification
from django.contrib import messages


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
        send_waiting_list_notification(
            waiting_entry.user.email,
            waiting_entry.swimling.name,
            lesson.name
        )

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
    send_waiting_list_notification(waiting_entry.user.email, waiting_entry.swimling.name, waiting_entry.product.name)
    return redirect('manage_waiting_list')


def waiting_list_success(request):
    return render(request, 'waiting_list/success.html')
