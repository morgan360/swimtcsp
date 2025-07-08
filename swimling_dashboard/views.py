from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect
from django.template.loader import render_to_string
from django.http import HttpResponse
from users.models import Swimling
from users.forms import NewSwimlingForm
from utils.context_processors import get_term_info
from lessons.models import Product  # adjust if needed
from lessons_bookings.models import LessonEnrollment
from users.helpers import fetch_waiting_list_data
from django.contrib import messages


# ✅ Main Dashboard
@login_required
def guardian_dashboard(request):
    swimlings = Swimling.objects.filter(guardian=request.user)
    term_info = get_term_info(request)
    current_term_id = term_info['current_term_id']
    next_term_id = term_info['next_term_id']
    current_phase = term_info['current_phase_id']

    public_lessons_data = []

    for swimling in swimlings:
        current_lessons = Product.objects.filter(
            enrollments__term_id=current_term_id,
            enrollments__swimling=swimling
        ).distinct()

        next_lessons = Product.objects.filter(
            enrollments__term_id=next_term_id,
            enrollments__swimling=swimling
        ).distinct()

        actions = []

        if current_phase in ['BK', 'RB']:
            actions.append({
                'label': 'Book Current',
                'url': f'/book/current/{swimling.id}/',
                'disabled': False
            })

        if current_phase == 'RB' and current_lessons.exists():
            actions.append({
                'label': 'Rebook',
                'url': f'/rebook/{swimling.id}/',
                'disabled': False
            })

        if current_phase == 'BN':
            actions.append({
                'label': 'Book Next',
                'url': f'/book/next/{swimling.id}/',
                'disabled': False
            })

        public_lessons_data.append({
            'swimling': swimling,
            'current_lessons': current_lessons,
            'next_lessons': next_lessons,
            'actions': actions
        })

    # ✅ Fetch waiting list entries
    waiting_list_data = fetch_waiting_list_data(request.user)

    return render(request, 'swimling_dashboard/dashboard.html', {
        'swimlings': swimlings,
        'public_lessons_data': public_lessons_data,
        'waiting_list_data': waiting_list_data,
        'show_waiting_list': bool(waiting_list_data),
        **term_info
    })


# ✅ HTMX: Add a Swimling (with live update)
@login_required
def add_swimling(request):
    if request.method == 'POST':
        form = NewSwimlingForm(request.POST)
        if form.is_valid():
            swimling = form.save(commit=False)
            swimling.guardian = request.user
            swimling.save()

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
                if current_phase in ['BK', 'RB'] and not current_lessons.exists():
                    actions.append({'label': 'Book Current', 'url': f'/book/current/{s.id}/', 'disabled': False})
                if current_phase == 'RB' and current_lessons.exists():
                    actions.append({'label': 'Rebook', 'url': f'/rebook/{s.id}/', 'disabled': False})
                if current_phase == 'BN':
                    actions.append({'label': 'Book Next', 'url': f'/book/next/{s.id}/', 'disabled': False})

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
        form = NewSwimlingForm()
        html = render_to_string('swimling_dashboard/_new_swimling_form.html', {'form': form}, request=request)
        return HttpResponse(html)



@login_required
def edit_swimling(request, id):
    swimling = get_object_or_404(Swimling, id=id, guardian=request.user)

    if request.method == 'POST':
        form = NewSwimlingForm(request.POST, instance=swimling)
        if form.is_valid():
            form.save()
            messages.success(request, 'Swimling updated successfully.')
            return redirect('swimling_dashboard:guardian_dashboard')
    else:
        form = NewSwimlingForm(instance=swimling)

    return render(request, 'swimling_dashboard/edit_swimling.html', {'form': form, 'swimling': swimling})


# ✅ HTMX: Refresh rebooking table
@login_required
def refresh_rebooking_table(request):
    # Add filtering if needed
    html = render_to_string('swimling_dashboard/_public_lessons_panel.html', {}, request=request)
    return HttpResponse(html)


# ✅ HTMX: Refresh waiting list table
@login_required
def refresh_waiting_list_panel(request):
    html = render_to_string('swimling_dashboard/_waiting_list_panel.html', {}, request=request)
    return HttpResponse(html)


# ✅ HTMX: Refresh school booking table
@login_required
def refresh_school_table(request):
    html = render_to_string('swimling_dashboard/_school_table.html', {}, request=request)
    return HttpResponse(html)
