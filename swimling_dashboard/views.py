from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from utils.context_processors import get_term_info
from lessons.models import Product
from lessons_bookings.models import LessonEnrollment
from users.helpers import fetch_waiting_list_data, collect_previous_lessons
from schools_bookings.utils.swimling_utils import (
    get_latest_active_school_term,
    swimling_is_enrolled,
)
from django.http import HttpResponse
from django.template.loader import render_to_string
from users.utils.roles import is_guardian
from users.forms import NewSwimlingForm
from django.contrib import messages
from django.http import HttpResponse
from schools_bookings.forms import DirectOrderForm
from schools.models import ScoLessons, ScoSchool
from schools_bookings.models import ScoTerm, ScoEnrollment
from users.models import Swimling
from django.shortcuts import redirect
from schools_orders.models import Order, OrderItem
from boipa.views import initiate_boipa_payment_session
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.urls import reverse
from .forms import SwimlingForm

@login_required
def school_checkout(request, swimling_id, term_id):
    swimling = get_object_or_404(Swimling, id=swimling_id)
    term = get_object_or_404(ScoTerm, id=term_id)
    school = get_object_or_404(ScoSchool, sco_role_num=swimling.sco_role_num)

    lessons = ScoLessons.objects.filter(school=school, active=True).order_by('day_of_week', 'start_time')

    if request.method == 'POST':
        form = DirectOrderForm(request.POST, lessons=lessons)
        if form.is_valid():
            lesson = form.cleaned_data['lesson']

            # ✅ Create the order
            order = Order.objects.create(
                user=request.user,
                amount=lesson.price,
                paid=False,
                school=school
            )

            # ✅ Create the order item
            OrderItem.objects.create(
                order=order,
                term=term,
                product=lesson,
                price=lesson.price,
                quantity=1,
                swimling=swimling
            )
            from django.core.mail import send_mail
            from django.template.loader import render_to_string

            # 📧 Build email content
            subject = f"School Booking Confirmation – {lesson.name}"
            to_email = request.user.email

            context = {
                'user': request.user,
                'lesson': lesson,
                'term': term,
                'swimling': swimling,
                'school': school,
                'order': order,
            }

            plain = render_to_string('emails/school_booking.txt', context)
            html = render_to_string('emails/school_booking.html', context)

            send_mail(
                subject=subject,
                message=plain,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[to_email],
                html_message=html
            )

            # Check if payment is needed
            if order.amount > 0:
                # Standard flow: send to BOIPA
                order_ref = f"school_{order.id}"
                return initiate_boipa_payment_session(request, order_ref, order.amount)
            else:
                # Zero-balance flow: order fully paid (free or fully discounted)
                from schools_bookings.utils.enrollment import handle_schools_enrollment
                from schools_orders.tasks import send_school_order_email
                order.paid = True
                order.save()
                handle_schools_enrollment(order)
                send_school_order_email(order.id)

                return render(request, 'orders/order/created.html', {
                    'order': order,
                    'order_items': order.items.all(),
                })

    else:
        form = DirectOrderForm(lessons=lessons)

    return render(request, 'schools_bookings/direct_order.html', {
        'form': form,
        'swimling': swimling,
        'term': term,
        'school': school,
    })


@login_required
def refresh_school_panel(request):
    swimlings = Swimling.objects.filter(guardian=request.user)
    current_term = ScoTerm.objects.filter(is_active=True).first()  # Get active term regardless of dates

    swimling_panels = []
    for swimling in swimlings:
        enrollment = ScoEnrollment.objects.filter(
            swimling=swimling,
            term=current_term
        ).select_related('lesson__school').first()

        swimling_panels.append({
            'swimling': swimling,
            'term': current_term,
            'is_enrolled': bool(enrollment),
            'lesson_name': enrollment.lesson.name if enrollment else None,
            'school_name': enrollment.lesson.school.name if enrollment else None,

        })

    html = render_to_string(
        'swimling_dashboard/_school_panel.html',
        {
            'school_panel_data': swimling_panels,
            'show_school_panel': True,
            'first_active_term': current_term,
        },
        request=request
    )
    return HttpResponse(html)



@login_required
def refresh_waiting_list_panel(request):
    try:
        # print("🔍 About to fetch waiting list data...")
        waiting_list_data = fetch_waiting_list_data(request.user)
        # print("✅ Fetched:", waiting_list_data)
    except Exception as e:
        print("❌ Error while fetching data:", e)
        return HttpResponse("⚠️ Error loading panel.", status=500)

    html = render_to_string(
        'swimling_dashboard/_waiting_list_panel.html',
        {"waiting_list_data": waiting_list_data},
        request=request
    )
    return HttpResponse(html)


@login_required
def refresh_rebooking_table(request):
    html = render_to_string('swimling_dashboard/_public_lessons_panel.html', {}, request=request)
    return HttpResponse(html)


@login_required
def edit_swimling(request, id):
    swimling = get_object_or_404(Swimling, id=id, guardian=request.user)

    if request.method == 'POST':
        form = NewSwimlingForm(request.POST, instance=swimling)
        if form.is_valid():
            form.save()
            messages.success(request, 'Swimling updated successfully.')
            
            # If this is an HTMX request, return a script to close modal and refresh page
            if request.headers.get('HX-Request'):
                return HttpResponse("""
                    <script>
                        closeEditSwimlingModal();
                        window.location.reload();
                    </script>
                """)
            
            return redirect('swimling_dashboard:guardian_dashboard')
    else:
        form = NewSwimlingForm(instance=swimling)

    return render(request, 'swimling_dashboard/edit_swimling.html', {'form': form, 'swimling': swimling})


@login_required
def add_swimling(request):
    if request.method == 'POST':
        form = SwimlingForm(request.POST)
        if form.is_valid():
            swimling = form.save(commit=False)
            swimling.guardian = request.user
            swimling.save()

            # rebuild dashboard data
            swimlings = Swimling.objects.filter(guardian=request.user)
            term_info = get_term_info(request)
            current_term_id = term_info['current_term_id']
            next_term_id = term_info['next_term_id']
            current_phase = term_info['current_phase_id']

            public_lessons_data = []
            for s in swimlings:
                current_lessons = Product.objects.filter(
                    enrollments__term_id=current_term_id,
                    enrollments__swimling=s
                ).distinct()
                next_lessons = Product.objects.filter(
                    enrollments__term_id=next_term_id,
                    enrollments__swimling=s
                ).distinct()

                actions = []
                # BK phase: Allow booking into current term only
                if current_phase == 'BK':
                    book_url = reverse('lessons:lesson_list') + f'?swimling={s.id}'
                    actions.append({'label': 'Book', 'url': book_url, 'disabled': False})

                # RB phase: Rebook for enrolled swimlings, Book for non-enrolled swimlings
                if current_phase == 'RB':
                    if current_lessons.exists():
                        # Swimling is enrolled → show Rebook button (goes to multi-select rebooking page)
                        actions.append({'label': 'Rebook', 'url': reverse('shopping_cart:rebooking_page'), 'disabled': False})
                    else:
                        # Swimling NOT enrolled → show Book button (books into current term)
                        book_url = reverse('lessons:lesson_list') + f'?swimling={s.id}'
                        actions.append({'label': 'Book', 'url': book_url, 'disabled': False})

                # BN phase: Allow booking into next term
                if current_phase == 'BN':
                    book_url = reverse('lessons:lesson_list') + f'?swimling={s.id}'
                    actions.append({'label': 'Book', 'url': book_url, 'disabled': False})

                public_lessons_data.append({
                    'swimling': s,
                    'current_lessons': current_lessons,
                    'next_lessons': next_lessons,
                    'actions': actions
                })

            html = render_to_string('swimling_dashboard/_dashboard_panels.html', {
                'swimlings': swimlings,
                'public_lessons_data': public_lessons_data,
                **term_info
            }, request=request)

            return HttpResponse(html)

        else:
            html = render_to_string('swimling_dashboard/_new_swimling_form.html', {'form': form}, request=request)
            return HttpResponse(html, status=400)

    else:
        print("🧪 GET request received for Add Swimling")
        form = SwimlingForm()
        html = render_to_string('swimling_dashboard/_new_swimling_form.html', {'form': form}, request=request)
        return HttpResponse(html)

@login_required
def guardian_dashboard(request):
    # 🚫 Block non-guardians
    if not is_guardian(request.user):
        messages.error(request, "Please become a guardian to access the swimling dashboard.")
        # Redirect to profile with context so user can upgrade easily
        profile_url = f"{reverse('users:profile')}?guardian_required=true&from=/dashboard/"
        return redirect(profile_url)

    swimlings = Swimling.objects.filter(guardian=request.user)
    term_info = get_term_info(request)
    current_term_id = term_info['current_term_id']
    next_term_id = term_info['next_term_id']
    current_phase = term_info['current_phase_id']
    school_group_names = ['schools', 'Schools', 'zion', 'bishopgalvin', 'bishop_galvin']
    is_school_user = request.user.groups.filter(name__in=school_group_names).exists()

    history_map = collect_previous_lessons(swimlings, current_term_id)
    for swimling in swimlings:
        setattr(swimling, 'previous_terms', history_map.get(swimling.id, []))

    public_lessons_data = []
    school_panel_data = []
    first_active_term = None

    for swimling in swimlings:
        # === Public Lessons Panel ===
        current_lessons = Product.objects.filter(
            enrollments__term_id=current_term_id,
            enrollments__swimling=swimling
        ).distinct()

        next_enrollments = (
            LessonEnrollment.objects
            .filter(term_id=next_term_id, swimling=swimling)
            .select_related('lesson', 'term')
        ) if next_term_id else LessonEnrollment.objects.none()

        next_lessons = []
        for enrollment in next_enrollments:
            lesson_obj = enrollment.lesson
            term_obj = enrollment.term
            next_lessons.append({
                'lesson': str(lesson_obj) if lesson_obj else '',
                'term_label': f"Term {term_obj.id}" if term_obj else None,
                'term_dates': (
                    f"{term_obj.start_date:%d %b} – {term_obj.end_date:%d %b %Y}"
                    if term_obj and term_obj.start_date and term_obj.end_date else None
                ),
            })

        actions = []
        # BK phase: Allow booking into current term only
        if current_phase == 'BK':
            url = reverse('lessons:lesson_list') + f'?swimling={swimling.id}'
            actions.append({'label': 'Book', 'url': url, 'disabled': False})

        # RB phase: Rebook for enrolled swimlings, Book for non-enrolled swimlings
        if current_phase == 'RB':
            if current_lessons.exists():
                # Swimling is enrolled → show Rebook button (goes to multi-select rebooking page)
                actions.append({'label': 'Rebook', 'url': reverse('shopping_cart:rebooking_page'), 'disabled': False})
            else:
                # Swimling NOT enrolled → show Book button (books into current term)
                url = reverse('lessons:lesson_list') + f'?swimling={swimling.id}'
                actions.append({'label': 'Book', 'url': url, 'disabled': False})

        # BN phase: Allow booking into next term
        if current_phase == 'BN':
            url = reverse('lessons:lesson_list') + f'?swimling={swimling.id}'
            actions.append({'label': 'Book', 'url': url, 'disabled': False})

        public_lessons_data.append({
            'swimling': swimling,
            'current_lessons': current_lessons,
            'next_lessons': next_lessons,
            'actions': actions
        })

        # === School Panel Logic ===
        if is_school_user and swimling.sco_role_num:
            term = None
            enrollment = None

            term_dates = None

            term = get_latest_active_school_term(swimling.sco_role_num)
            if term and not first_active_term:
                first_active_term = term
            if term and term.start_date and term.end_date:
                term_dates = f"{term.start_date:%d %b %Y} – {term.end_date:%d %b %Y}"
            if term:
                enrollment = (
                    ScoEnrollment.objects
                    .filter(swimling=swimling, term=term)
                    .select_related('lesson__school')
                    .first()
                )

            school_panel_data.append({
                'swimling': swimling,
                'term': term,
                'has_role_number': True,
                'is_enrolled': bool(enrollment),
                'lesson_name': enrollment.lesson.name if enrollment else None,
                'school_name': enrollment.lesson.school.name if enrollment else None,
                'term_dates': term_dates,
            })

    context = {
        'show_school_panel': is_school_user,
        'public_lessons_data': public_lessons_data,
        'school_panel_data': school_panel_data,
        'first_active_term': first_active_term,
    }

    return render(request, 'swimling_dashboard/dashboard.html', context)

    # ✅ Waiting List Panel
    waiting_list_data = fetch_waiting_list_data(request.user)

    return render(request, 'swimling_dashboard/dashboard.html', {
        'swimlings': swimlings,
        'public_lessons_data': public_lessons_data,
        'waiting_list_data': waiting_list_data,
        'show_waiting_list': bool(waiting_list_data),
        'school_panel_data': school_panel_data,
        'show_school_panel': is_school_user,
        **term_info
    })
