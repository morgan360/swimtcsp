import logging
import re
from collections import defaultdict
from decimal import Decimal

logger = logging.getLogger('finances')

from django.db.models import F, Sum, Count
from django.db.models.functions import TruncDay, TruncWeek, TruncMonth, TruncYear
from django.utils.timezone import now, timedelta
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponse
from django.utils.timezone import localtime, make_aware
import datetime

from swims_orders.models import Order  # ✅ your Order model
from lessons_orders.models import Order as LessonOrder
from schools_orders.models import Order as SchoolOrder

ORDER_MODELS = {
    'lesson': (LessonOrder, 'Lesson'),
    'swim': (Order, 'Swim'),
    'school': (SchoolOrder, 'School'),
}


@staff_member_required
def transactions_data(request):
    """
    Return JSON for DataTables with optional period filter
    """
    data = []
    orders = Order.objects.select_related("user", "product")

    # Check filter
    period = request.GET.get("period")
    today = localtime(now()).date()

    if period == "today":
        start = make_aware(datetime.datetime.combine(today, datetime.time.min))
        orders = orders.filter(created__gte=start)
    elif period == "week":
        week_start = today - timedelta(days=today.weekday())
        start = make_aware(datetime.datetime.combine(week_start, datetime.time.min))
        orders = orders.filter(created__gte=start)
    elif period == "month":
        month_start = today.replace(day=1)
        start = make_aware(datetime.datetime.combine(month_start, datetime.time.min))
        orders = orders.filter(created__gte=start)

    orders = orders.order_by("-created")[:500]

    for o in orders:
        data.append({
            "date": localtime(o.created).strftime("%Y-%m-%d %H:%M"),
            "guardian": getattr(o.user, "email", str(o.user)),
            "amount": float(o.amount),
            "product": o.product.name if o.product else "",
            "status": "Paid" if o.paid else "Unpaid",
        })

    return JsonResponse({"data": data})


@staff_member_required
def dashboard(request):
    today = localtime(now()).date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # Create datetime ranges in the correct timezone
    start_of_today = make_aware(datetime.datetime.combine(today, datetime.time.min))
    start_of_week = make_aware(datetime.datetime.combine(week_start, datetime.time.min))
    start_of_month = make_aware(datetime.datetime.combine(month_start, datetime.time.min))

    qs = Order.objects.filter(paid=True)

    today_rev = qs.filter(created__gte=start_of_today).aggregate(Sum("amount"))["amount__sum"] or 0
    week_rev = qs.filter(created__gte=start_of_week).aggregate(Sum("amount"))["amount__sum"] or 0
    month_rev = qs.filter(created__gte=start_of_month).aggregate(Sum("amount"))["amount__sum"] or 0

    context = {
        "today_rev": today_rev,
        "week_rev": week_rev,
        "month_rev": month_rev,
    }
    return render(request, "finances/dashboard.html", context)


# ---------------------------------------------------------------------------
# Combined Revenue Report
# ---------------------------------------------------------------------------

TRUNC_MAP = {
    'day': TruncDay,
    'week': TruncWeek,
    'month': TruncMonth,
    'year': TruncYear,
}


def _aggregate_orders(model, trunc_fn, year, month=None):
    """Aggregate paid orders for a single Order model by period."""
    qs = model.objects.filter(paid=True, created__year=year)
    if month:
        qs = qs.filter(created__month=month)
    return (
        qs.annotate(period=trunc_fn('created'))
        .values('period')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('period')
    )


def _build_revenue_data(granularity, year, month=None):
    """Build combined revenue rows from all three order types."""
    trunc_fn = TRUNC_MAP.get(granularity, TruncMonth)

    combined = defaultdict(lambda: {
        'lessons': Decimal('0'), 'swims': Decimal('0'), 'schools': Decimal('0'),
        'lessons_count': 0, 'swims_count': 0, 'schools_count': 0,
    })

    for row in _aggregate_orders(LessonOrder, trunc_fn, year, month):
        combined[row['period']]['lessons'] = row['total'] or Decimal('0')
        combined[row['period']]['lessons_count'] = row['count']

    for row in _aggregate_orders(Order, trunc_fn, year, month):
        combined[row['period']]['swims'] = row['total'] or Decimal('0')
        combined[row['period']]['swims_count'] = row['count']

    for row in _aggregate_orders(SchoolOrder, trunc_fn, year, month):
        combined[row['period']]['schools'] = row['total'] or Decimal('0')
        combined[row['period']]['schools_count'] = row['count']

    rows = []
    for period in sorted(combined.keys(), reverse=True):
        d = combined[period]
        total = d['lessons'] + d['swims'] + d['schools']
        total_count = d['lessons_count'] + d['swims_count'] + d['schools_count']
        rows.append({
            'period': period,
            'lessons': d['lessons'],
            'swims': d['swims'],
            'schools': d['schools'],
            'total': total,
            'count': total_count,
        })

    summary = {
        'lessons_total': sum(r['lessons'] for r in rows),
        'swims_total': sum(r['swims'] for r in rows),
        'schools_total': sum(r['schools'] for r in rows),
        'grand_total': sum(r['total'] for r in rows),
        'order_count': sum(r['count'] for r in rows),
    }
    return rows, summary


def _format_period_label(period, granularity):
    """Format a period datetime for display."""
    if granularity == 'day':
        return period.strftime('%a %d %b')
    elif granularity == 'week':
        return f"W{period.isocalendar()[1]} ({period.strftime('%d %b')})"
    elif granularity == 'month':
        return period.strftime('%b %Y')
    else:
        return period.strftime('%Y')


def _get_available_years():
    """Return list of years that have any paid orders."""
    years = set()
    for model in [LessonOrder, Order, SchoolOrder]:
        qs = model.objects.filter(paid=True).dates('created', 'year')
        years.update(d.year for d in qs)
    return sorted(years, reverse=True) if years else [localtime(now()).year]


@staff_member_required
def revenue_report(request, template_name='finances/revenue_report.html'):
    """Main revenue report page."""
    available_years = _get_available_years()
    year = int(request.GET.get('year', localtime(now()).year))
    granularity = request.GET.get('granularity', 'month')
    month = request.GET.get('month', '')
    month = int(month) if month else None

    rows, summary = _build_revenue_data(granularity, year, month)

    # Format period labels
    for row in rows:
        row['label'] = _format_period_label(row['period'], granularity)

    today = localtime(now()).date()
    yesterday = today - timedelta(days=1)

    context = {
        'rows': rows,
        'summary': summary,
        'granularity': granularity,
        'year': year,
        'month': month or '',
        'available_years': available_years,
        'months': [
            (i, datetime.date(2000, i, 1).strftime('%B')) for i in range(1, 13)
        ],
        'today': today.isoformat(),
        'yesterday': yesterday.isoformat(),
    }
    return render(request, template_name, context)


@staff_member_required
def revenue_report_table(request):
    """HTMX partial: just the table + summary cards."""
    year = int(request.GET.get('year', localtime(now()).year))
    granularity = request.GET.get('granularity', 'month')
    month = request.GET.get('month', '')
    month = int(month) if month else None

    rows, summary = _build_revenue_data(granularity, year, month)
    for row in rows:
        row['label'] = _format_period_label(row['period'], granularity)

    context = {
        'rows': rows,
        'summary': summary,
        'granularity': granularity,
        'year': year,
        'month': month or '',
    }
    return render(request, 'finances/partials/revenue_table.html', context)


@staff_member_required
def revenue_chart_data(request):
    """JSON endpoint for Chart.js."""
    year = int(request.GET.get('year', localtime(now()).year))
    granularity = request.GET.get('granularity', 'month')
    month = request.GET.get('month', '')
    month = int(month) if month else None

    rows, summary = _build_revenue_data(granularity, year, month)

    # Chart needs chronological order (oldest first)
    chart_rows = list(reversed(rows))
    labels = [_format_period_label(r['period'], granularity) for r in chart_rows]
    datasets = {
        'lessons': [float(r['lessons']) for r in chart_rows],
        'swims': [float(r['swims']) for r in chart_rows],
        'schools': [float(r['schools']) for r in chart_rows],
        'total': [float(r['total']) for r in chart_rows],
    }

    return JsonResponse({
        'labels': labels,
        'datasets': datasets,
        'summary': {k: float(v) for k, v in summary.items()},
    })


@staff_member_required
def revenue_daily_orders(request):
    """HTMX partial: list individual orders for a specific date."""
    if not request.user.is_staff:
        return HttpResponse('Unauthorized', status=403)

    date_str = request.GET.get('date', '')
    try:
        target_date = datetime.datetime.strptime(date_str, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        target_date = localtime(now()).date()

    orders = []
    for type_key, (model, type_label) in ORDER_MODELS.items():
        qs = model.objects.filter(
            paid=True,
            created__date=target_date,
        ).select_related('user').order_by('-created')
        for o in qs:
            orders.append({
                'type_label': type_label,
                'order_id': o.id,
                'created': o.created,
                'user_email': getattr(o.user, 'email', '—'),
                'amount': o.amount,
            })

    orders.sort(key=lambda x: x['created'], reverse=True)
    total = sum(o['amount'] for o in orders)

    context = {
        'orders': orders,
        'target_date': target_date,
        'total': total,
        'order_count': len(orders),
    }
    return render(request, 'finances/partials/revenue_daily_orders.html', context)


@staff_member_required
def revenue_export_csv(request):
    """Export revenue report as CSV."""
    import csv

    year = int(request.GET.get('year', localtime(now()).year))
    granularity = request.GET.get('granularity', 'month')
    month = request.GET.get('month', '')
    month = int(month) if month else None

    rows, summary = _build_revenue_data(granularity, year, month)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="revenue_{granularity}_{year}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Period', 'Lessons', 'Swims', 'Schools', 'Total', 'Orders'])
    for row in rows:
        writer.writerow([
            _format_period_label(row['period'], granularity),
            row['lessons'], row['swims'], row['schools'],
            row['total'], row['count'],
        ])
    writer.writerow([])
    writer.writerow([
        'TOTALS', summary['lessons_total'], summary['swims_total'],
        summary['schools_total'], summary['grand_total'], summary['order_count'],
    ])
    return response


# ---------------------------------------------------------------------------
# BOIPA Reconciliation
# ---------------------------------------------------------------------------

def _classify_orders(start_date, end_date, order_type_filter='all'):
    """Cross-reference paid orders with BOIPA payment notifications."""
    results = []

    models_to_check = ORDER_MODELS.items()
    if order_type_filter != 'all' and order_type_filter in ORDER_MODELS:
        models_to_check = [(order_type_filter, ORDER_MODELS[order_type_filter])]

    for type_key, (model, type_label) in models_to_check:
        orders = (
            model.objects.filter(paid=True, created__date__gte=start_date, created__date__lte=end_date)
            .prefetch_related('notifications')
            .select_related('user')
            .order_by('-created')
        )

        for order in orders:
            notifications = list(order.notifications.all())
            tx_id = getattr(order, 'txId', '') or ''

            if not tx_id:
                category = 'no_txid'
                notif_amount = None
                difference = None
            elif not notifications and not getattr(order, 'boipa_reconciled', False):
                category = 'missing_notification'
                notif_amount = None
                difference = None
            elif not notifications and getattr(order, 'boipa_reconciled', False):
                # Verified via API but no notification record saved (verified before fix)
                category = 'matched'
                notif_amount = order.amount
                difference = Decimal('0')
            else:
                # Find the best notification (prefer CAPTURED status)
                captured = [n for n in notifications if (n.status or '').upper() == 'CAPTURED']
                best = captured[0] if captured else notifications[0]
                notif_amount = best.amount

                if notif_amount is not None and notif_amount == order.amount:
                    category = 'matched'
                    difference = Decimal('0')
                else:
                    category = 'mismatched'
                    difference = (order.amount - notif_amount) if notif_amount is not None else None

            results.append({
                'order_id': order.id,
                'order_type': type_key,
                'type_label': type_label,
                'created': order.created,
                'user_email': getattr(order.user, 'email', '—'),
                'order_amount': order.amount,
                'notif_amount': notif_amount,
                'difference': difference,
                'category': category,
                'tx_id': tx_id,
                'reconciled': getattr(order, 'boipa_reconciled', False),
                'notification_count': len(notifications),
            })

    # Sort by date descending
    results.sort(key=lambda r: r['created'], reverse=True)

    # Summary
    summary = {
        'matched': {'count': 0, 'amount': Decimal('0')},
        'mismatched': {'count': 0, 'amount': Decimal('0')},
        'missing_notification': {'count': 0, 'amount': Decimal('0')},
        'no_txid': {'count': 0, 'amount': Decimal('0')},
    }
    for r in results:
        cat = r['category']
        summary[cat]['count'] += 1
        summary[cat]['amount'] += r['order_amount']

    return results, summary


def _parse_reconciliation_params(request):
    """Extract common filter params from request."""
    today = localtime(now()).date()
    start_date = request.GET.get('start_date', '')
    end_date = request.GET.get('end_date', '')

    try:
        start_date = datetime.date.fromisoformat(start_date)
    except (ValueError, TypeError):
        start_date = today - datetime.timedelta(days=30)

    try:
        end_date = datetime.date.fromisoformat(end_date)
    except (ValueError, TypeError):
        end_date = today

    order_type = request.GET.get('order_type', 'all')
    category = request.GET.get('category', 'problems')

    return start_date, end_date, order_type, category


@staff_member_required
def reconciliation_dashboard(request, template_name='finances/reconciliation.html'):
    """Main reconciliation page."""
    start_date, end_date, order_type, category = _parse_reconciliation_params(request)

    results, summary = _classify_orders(start_date, end_date, order_type)

    # Filter by category
    if category == 'problems':
        filtered = [r for r in results if r['category'] != 'matched']
    elif category != 'all':
        filtered = [r for r in results if r['category'] == category]
    else:
        filtered = results

    context = {
        'results': filtered,
        'summary': summary,
        'start_date': start_date.isoformat(),
        'end_date': end_date.isoformat(),
        'order_type': order_type,
        'category': category,
        'total_orders': len(results),
    }
    return render(request, template_name, context)


@staff_member_required
def reconciliation_table(request):
    """HTMX partial for reconciliation table."""
    start_date, end_date, order_type, category = _parse_reconciliation_params(request)

    results, summary = _classify_orders(start_date, end_date, order_type)

    if category == 'problems':
        filtered = [r for r in results if r['category'] != 'matched']
    elif category != 'all':
        filtered = [r for r in results if r['category'] == category]
    else:
        filtered = results

    context = {
        'results': filtered,
        'summary': summary,
        'total_orders': len(results),
    }
    return render(request, 'finances/partials/reconciliation_table.html', context)


def reconciliation_verify(request, order_type, order_id):
    """Verify a single order with BOIPA API and return updated row."""
    # Manual auth check instead of @staff_member_required to avoid redirect in HTMX
    if not request.user.is_authenticated or not request.user.is_staff:
        return HttpResponse(
            '<td colspan="10" class="px-4 py-2 text-center text-red-600">Authentication required. Please refresh the page.</td>',
            status=200,
        )

    if request.method != 'POST':
        return HttpResponse('Method not allowed', status=405)

    model_info = ORDER_MODELS.get(order_type)
    if not model_info:
        return HttpResponse('Invalid order type', status=400)

    model, type_label = model_info
    try:
        order = model.objects.prefetch_related('notifications').select_related('user').get(id=order_id)
    except model.DoesNotExist:
        return HttpResponse('Order not found', status=404)

    tx_id = getattr(order, 'txId', '') or ''
    verified = False
    verify_error = None
    boipa_amount = None
    if tx_id:
        try:
            from boipa.utils import get_boipa_transaction_details
            details = get_boipa_transaction_details(tx_id)
            if details:
                verified = details['captured']
                boipa_amount = details.get('amount')
                order.boipa_reconciled = verified
                order.save(update_fields=['boipa_reconciled'])

                # Save a notification record so the data persists on reload
                if boipa_amount is not None:
                    from boipa.models import (
                        SwimOrderPaymentNotification,
                        LessonOrderPaymentNotification,
                        SchoolOrderPaymentNotification,
                    )
                    notif_model_map = {
                        'swim': SwimOrderPaymentNotification,
                        'lesson': LessonOrderPaymentNotification,
                        'school': SchoolOrderPaymentNotification,
                    }
                    NotifModel = notif_model_map.get(order_type)
                    if NotifModel and not NotifModel.objects.filter(order=order, txId=tx_id).exists():
                        try:
                            NotifModel.objects.create(
                                order=order,
                                txId=tx_id,
                                merchantTxId='',
                                amount=boipa_amount,
                                currency=details.get('currency', 'EUR'),
                                status=details.get('status', 'CAPTURED'),
                                errorMessage='Created from API verification',
                            )
                        except Exception as e:
                            logger.warning(f"Failed to save notification from verify: {e}")
            else:
                verify_error = 'No response from BOIPA API'
        except Exception as e:
            verify_error = str(e)

    # Rebuild classification for this single order
    # Use BOIPA API amount if available, otherwise fall back to notifications
    notifications = list(order.notifications.all())
    if not tx_id:
        cat = 'no_txid'
        notif_amount = None
        difference = None
    else:
        # Prefer the amount from BOIPA API (just verified), then notifications
        if boipa_amount is not None:
            notif_amount = boipa_amount
        elif notifications:
            captured = [n for n in notifications if (n.status or '').upper() == 'CAPTURED']
            best = captured[0] if captured else notifications[0]
            notif_amount = best.amount
        else:
            notif_amount = None

        if notif_amount is not None and notif_amount == order.amount:
            cat = 'matched'
            difference = Decimal('0')
        elif notif_amount is not None:
            cat = 'mismatched'
            difference = order.amount - notif_amount
        else:
            cat = 'missing_notification'
            difference = None

    row = {
        'order_id': order.id,
        'order_type': order_type,
        'type_label': type_label,
        'created': order.created,
        'user_email': getattr(order.user, 'email', '—'),
        'order_amount': order.amount,
        'notif_amount': notif_amount,
        'difference': difference,
        'category': cat,
        'tx_id': tx_id,
        'reconciled': order.boipa_reconciled,
        'verify_error': verify_error,
        'notification_count': len(notifications),
    }
    return render(request, 'finances/partials/reconciliation_row.html', {'row': row})


def reconciliation_details(request, order_type, order_id):
    """HTMX partial: return notification details for an order."""
    if not request.user.is_staff:
        return HttpResponse('<span class="text-xs text-red-500">Unauthorized</span>', status=403)
    model_info = ORDER_MODELS.get(order_type)
    if not model_info:
        return HttpResponse('Invalid order type', status=400)

    model, type_label = model_info
    try:
        order = model.objects.prefetch_related('notifications').get(id=order_id)
    except model.DoesNotExist:
        return HttpResponse('Order not found', status=404)

    notifications = list(order.notifications.all().order_by('-id'))

    context = {
        'order': order,
        'order_type': order_type,
        'type_label': type_label,
        'notifications': notifications,
    }
    return render(request, 'finances/partials/reconciliation_details.html', context)


@staff_member_required
def reconciliation_export_csv(request):
    """Export reconciliation results as CSV."""
    import csv

    start_date, end_date, order_type, category = _parse_reconciliation_params(request)
    results, summary = _classify_orders(start_date, end_date, order_type)

    if category == 'problems':
        filtered = [r for r in results if r['category'] != 'matched']
    elif category != 'all':
        filtered = [r for r in results if r['category'] == category]
    else:
        filtered = results

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="reconciliation_{start_date}_{end_date}.csv"'

    writer = csv.writer(response)
    writer.writerow(['Type', 'Order #', 'Date', 'User', 'Order Amount', 'BOIPA Amount', 'Difference', 'Category', 'TxId', 'Reconciled'])
    for r in filtered:
        writer.writerow([
            r['type_label'], r['order_id'],
            localtime(r['created']).strftime('%Y-%m-%d %H:%M'),
            r['user_email'], r['order_amount'],
            r['notif_amount'] or '—',
            r['difference'] if r['difference'] is not None else '—',
            r['category'], r['tx_id'],
            'Yes' if r['reconciled'] else 'No',
        ])
    return response

# ---------------------------------------------------------------------------
# Lesson enrollments
# ---------------------------------------------------------------------------

def _fill_pct(enrolled, places):
    """Whole-number fill percentage, or None when the lesson has no capacity set."""
    if not places:
        return None
    return round(enrolled * 100 / places)


def _enrollment_terms():
    """Last, this and next term — whichever of them exist.

    Between terms there is no current term, and the next one may not have been
    created yet, so the list can hold anywhere from zero to three entries.
    """
    from lessons_bookings.models import Term

    candidates = [
        ('Last term', Term.get_previous_term()),
        ('This term', Term.get_current_term()),
        ('Next term', Term.get_next_term()),
    ]
    return [(label, term) for label, term in candidates if term]


@staff_member_required
def lesson_enrollments(request, template_name='admin/financeadmin/lesson_enrollments.html'):
    """Enrollment totals per term, and how full each lesson is in each term."""
    from lessons.models import Product
    from lessons_bookings.models import LessonEnrollment

    terms = _enrollment_terms()
    term_ids = [term.id for _, term in terms]

    counts = defaultdict(int)  # (lesson_id, term_id) -> enrolled
    for row in (LessonEnrollment.objects.filter(term_id__in=term_ids)
                .values('lesson_id', 'term_id').annotate(n=Count('id'))):
        counts[(row['lesson_id'], row['term_id'])] = row['n']

    # Active lessons, plus any since-retired lesson that still had swimmers in
    # one of these terms — otherwise last term's numbers would not add up.
    enrolled_lesson_ids = {lesson_id for lesson_id, _ in counts}
    lessons = (Product.objects.filter(active=True) | Product.objects.filter(id__in=enrolled_lesson_ids))
    lessons = lessons.select_related('category').distinct().order_by('day_of_week', 'start_time', 'category__name')

    rows = []
    totals = {term.id: {'enrolled': 0, 'places': 0} for _, term in terms}
    for lesson in lessons:
        cells = []
        for _, term in terms:
            enrolled = counts[(lesson.id, term.id)]
            # A lesson counts towards a term's capacity if it was running then:
            # it is active, or it has swimmers in that term.
            running = lesson.active or enrolled > 0
            places = lesson.num_places or 0
            if running:
                totals[term.id]['enrolled'] += enrolled
                totals[term.id]['places'] += places
            pct = _fill_pct(enrolled, places) if running else None
            cells.append({
                'enrolled': enrolled,
                'places': lesson.num_places,
                'running': running,
                'pct': pct,
                'bar_width': min(pct or 0, 100),
            })
        rows.append({
            'lesson': lesson,
            'category': lesson.category.short_name or lesson.category.name,
            'day': lesson.get_day_of_week_display(),
            'time': lesson.start_time.strftime('%H:%M') if lesson.start_time else '',
            'active': lesson.active,
            'cells': cells,
        })

    term_summaries = []
    for label, term in terms:
        t = totals[term.id]
        term_summaries.append({
            'label': label,
            'term': term,
            'enrolled': t['enrolled'],
            'places': t['places'],
            'pct': _fill_pct(t['enrolled'], t['places']),
        })

    chart_data = {
        'labels': [f"{s['label']} ({s['term'].start_date:%d %b} – {s['term'].end_date:%d %b %Y})"
                   if s['term'].start_date and s['term'].end_date else s['label']
                   for s in term_summaries],
        'enrolled': [s['enrolled'] for s in term_summaries],
        'places': [s['places'] for s in term_summaries],
    }

    context = {
        'term_summaries': term_summaries,
        'rows': rows,
        'chart_data': chart_data,
    }
    return render(request, template_name, context)


# ---------------------------------------------------------------------------
# Daily activity
# ---------------------------------------------------------------------------

def _activity_periods(today=None):
    """(label, start, end) for today, yesterday and this week (Monday to today), in local time."""
    today = today or localtime(now()).date()

    def start_of(day):
        return make_aware(datetime.datetime.combine(day, datetime.time.min))

    tomorrow = today + timedelta(days=1)
    return [
        ('Today', start_of(today), start_of(tomorrow)),
        ('Yesterday', start_of(today - timedelta(days=1)), start_of(today)),
        ('This week', start_of(today - timedelta(days=today.weekday())), start_of(tomorrow)),
    ]


def _period_counts(queryset, periods, field='created', distinct=None):
    """How many rows fall in each period, or how many distinct ``distinct`` values."""
    values = []
    for _, start, end in periods:
        qs = queryset.filter(**{f'{field}__gte': start, f'{field}__lt': end})
        values.append(qs.values(distinct).distinct().count() if distinct else qs.count())
    return values


def _paid_orders(model, periods):
    """([order count], [revenue]) per period for one order model."""
    # A refund leaves paid=True, so it is excluded by status.
    qs = model.objects.filter(paid=True).exclude(payment_status='refunded')
    orders, revenue = [], []
    for _, start, end in periods:
        agg = qs.filter(created__gte=start, created__lt=end).aggregate(n=Count('id'), total=Sum('amount'))
        orders.append(agg['n'])
        revenue.append(agg['total'] or Decimal('0'))
    return orders, revenue


def _checkout_funnel(start, end):
    """Customers who reached the payment page between ``start`` and ``end``, and how it ended.

    Checkout creates the order and then sends the customer to BOIPA, so an order is
    a visit to the payment page. Counted in people, not orders: an unpaid attempt and
    a successful retry is one finished checkout, and also counts as a retry. Declines
    are not split out: BOIPA does not report them back, so they would always read 0.
    Orders for €0 (fully couponed) never reach BOIPA and are left out, as are orders
    staff placed for a customer.
    """
    started, finished, unpaid = set(), set(), set()
    for model, _ in ORDER_MODELS.values():
        orders = model.objects.filter(created__gte=start, created__lt=end, amount__gt=0,
                                      user__is_staff=False)
        started.update(orders.values_list('user_id', flat=True))
        finished.update(orders.filter(paid=True).values_list('user_id', flat=True))
        unpaid.update(orders.filter(paid=False).values_list('user_id', flat=True))
    return {'started': len(started), 'finished': len(finished),
            'retried': len(finished & unpaid), 'left': len(started - finished)}


@staff_member_required
def activity_report(request, template_name='admin/financeadmin/activity_report.html'):
    """What happened on the site today, yesterday and this week."""
    from django.contrib.auth import get_user_model
    from custom_admins.financeadmin import finance_admin_site
    from lessons_bookings.models import LessonEnrollment
    from schools_bookings.models import ScoEnrollment
    from users.models import ActiveDay, LoginEvent

    User = get_user_model()
    periods = _activity_periods()

    def counts(queryset, field='created', distinct=None):
        return _period_counts(queryset, periods, field, distinct)

    def row(label, values, money=False, hint=''):
        return {'label': label, 'values': values, 'money': money, 'hint': hint}

    order_rows = {key: _paid_orders(model, periods) for key, (model, _) in ORDER_MODELS.items()}

    def total(index):
        return [sum(col) for col in zip(*(order_rows[key][index] for key in order_rows))]

    logins = LoginEvent.objects.all()
    active = ActiveDay.objects.all()
    staff_changes = {'changed_by__is_staff': True}
    sections = [
        ('🏊 Public swims', [
            row('Paid orders', order_rows['swim'][0]),
            row('Revenue', order_rows['swim'][1], money=True),
            row('Check-ins', counts(Order.objects.all(), field='checked_in_at')),
        ]),
        ('📚 Lessons', [
            row('Paid orders', order_rows['lesson'][0]),
            row('Revenue', order_rows['lesson'][1], money=True),
            row('New enrollments', counts(LessonEnrollment.objects.all())),
        ]),
        ('🏫 Schools', [
            row('Paid orders', order_rows['school'][0]),
            row('Revenue', order_rows['school'][1], money=True),
            row('New enrollments', counts(ScoEnrollment.objects.all())),
        ]),
        ('💶 All orders', [
            row('Paid orders', total(0)),
            row('Revenue', total(1), money=True, hint='Refunded orders are left out'),
        ]),
        ('👪 Customers', [
            row('Active customers', counts(active.filter(user__is_staff=False), field='date', distinct='user'),
                hint='Used the site while logged in'),
            row('Logins', counts(logins.filter(user__is_staff=False))),
            row('Customers who logged in', counts(logins.filter(user__is_staff=False), distinct='user')),
            row('New sign-ups', counts(User.objects.filter(is_staff=False), field='date_joined')),
        ]),
        ('🧑‍💼 Staff', [
            row('Active staff', counts(active.filter(user__is_staff=True), field='date', distinct='user'),
                hint='Used the site while logged in'),
            row('Logins', counts(logins.filter(user__is_staff=True))),
            row('Staff who logged in', counts(logins.filter(user__is_staff=True), distinct='user')),
            row('Lesson enrollments changed', counts(LessonEnrollment.objects.filter(**staff_changes), field='updated'),
                hint='Added, moved or edited by a staff member'),
            row('School enrollments changed', counts(ScoEnrollment.objects.filter(**staff_changes), field='updated')),
        ]),
    ]

    first_login = LoginEvent.objects.order_by('created').values_list('created', flat=True).first()
    first_active = ActiveDay.objects.order_by('date').values_list('date', flat=True).first()
    context = {
        **finance_admin_site.each_context(request),
        'title': 'Daily Activity',
        'periods': periods,
        'sections': sections,
        'logins_since': first_login,
        'active_since': first_active,
    }
    return render(request, template_name, context)


# ---------------------------------------------------------------------------
# Live dashboard
# ---------------------------------------------------------------------------

DASHBOARD_DAYS = 14
NEARLY_FULL_PCT = 90
RECENT_CHAT_QUESTIONS = 8

# ChatbotQuery.response_type, in the order the chart stacks them.
CHAT_TYPES = {
    'FAQ': 'FAQ answer',
    'FAQ_HEDGED': 'FAQ, unsure',
    'GPT': 'AI model',
    'BLOCKED': 'Blocked',
}

# What chat questions are about, by keyword: the first topic whose words appear
# wins, so the specific topics come before the catch-all "when/today" one.
# Keywords match at the start of a word, so "book" also catches "booking".
CHAT_TOPICS = [
    ('Prices & discounts', ('price', 'cost', 'how much', 'fee', 'euro', 'discount', 'student', 'oap',
                            'senior', 'half price', 'rate', 'pay', 'cheap', 'free')),
    ('Masters, aqua & other classes', ('master', 'aqua', 'lifeguard', 'life guard', 'party', 'parties',
                                       'club', 'coached', 'intens', 'training', 'team')),
    ('Pool, facilities & what to bring', ('locker', 'shower', 'changing', 'water', 'warm', 'heat', 'facilit',
                                          'parking', 'towel', 'goggle', 'trunks', 'baby', 'toilet', 'hair',
                                          'hat', 'swim cap', 'wear', 'bring', 'length', 'width',
                                          'busy', 'busiest')),
    ('Booking & changes', ('book', 'rebook', 'cancel', 'change', 'wait list', 'waiting list', 'waitlist',
                           'register', 'sign up', 'sign my', 'enrol', 'order', 'refund', 'login', 'log in',
                           'account', 'pause', 'holiday', 'member')),
    ('Lesson levels & ages', ('level', 'beginner', 'improver', 'prover', 'stage', 'year old', 'age', 'kids',
                              'child', 'adult', 'learn', 'difference')),
    ('Swim times & opening', ('time', 'today', 'tomorrow', 'tonight', 'open', 'closed', 'timetable',
                              'schedule', 'when', 'available', 'availability', 'walk in', 'monday',
                              'tuesday', 'wednesday', 'thursday', 'friday', 'saturday', 'sunday', 'weekend',
                              'christmas', 'term', 'session')),
]
CHAT_TOPIC_PATTERNS = [
    (name, re.compile(r'\b(?:' + '|'.join(re.escape(word) for word in words) + ')', re.IGNORECASE))
    for name, words in CHAT_TOPICS
]
TOP_CHAT_TOPICS = 3


def _chat_topic(message):
    for name, pattern in CHAT_TOPIC_PATTERNS:
        if pattern.search(message):
            return name
    return None


def _chat_summary(chats):
    """All-time totals and the most common topics. Blocked messages are left out of the topics."""
    from collections import Counter

    types = dict(chats.values_list('response_type').annotate(n=Count('id')))
    total = sum(types.values())
    if not total:
        return None
    messages = chats.exclude(response_type='BLOCKED').values_list('message', flat=True)
    topics = Counter(_chat_topic(message) for message in messages)
    asked = sum(topics.values()) or 1
    unsorted = topics.pop(None, 0)
    faq = types.get('FAQ', 0) + types.get('FAQ_HEDGED', 0)
    top = topics.most_common(TOP_CHAT_TOPICS)
    return {
        'total': total,
        'since': chats.order_by('timestamp').values_list('timestamp', flat=True).first(),
        'faq_pct': round(faq * 100 / total),
        # The bar is scaled to the most common topic, so the three are easy to compare.
        'top': [{'name': name, 'count': n, 'pct': round(n * 100 / asked), 'bar': round(n * 100 / top[0][1])}
                for name, n in top],
        'unsorted_pct': round(unsorted * 100 / asked),
    }


CHAT_RATING_DAYS = 30
RECENT_UNHELPFUL = 5


def _chat_ratings(chats, today):
    """Visitors' thumbs up and down over the last CHAT_RATING_DAYS, or None if none.

    Split by where the answer came from, since a poor FAQ answer is fixed by
    editing the FAQ and a poor AI answer usually by adding one.
    """
    from chatbot.models import ChatbotQuery

    since = make_aware(datetime.datetime.combine(today - timedelta(days=CHAT_RATING_DAYS - 1), datetime.time.min))
    rated = chats.filter(rating__isnull=False, rated_at__gte=since)
    if not rated.exists():
        return None

    def counts(qs):
        helpful = qs.filter(rating=ChatbotQuery.HELPFUL).count()
        unhelpful = qs.filter(rating=ChatbotQuery.UNHELPFUL).count()
        total = helpful + unhelpful
        return {'helpful': helpful, 'unhelpful': unhelpful,
                'pct': round(helpful * 100 / total) if total else None}

    unhelpful = rated.filter(rating=ChatbotQuery.UNHELPFUL).order_by('-rated_at')[:RECENT_UNHELPFUL]
    return {
        'days': CHAT_RATING_DAYS,
        'all': counts(rated),
        'faq': counts(rated.filter(response_type__in=['FAQ', 'FAQ_HEDGED'])),
        'ai': counts(rated.filter(response_type='GPT')),
        'unhelpful': [{'when': chat.rated_at, 'kind': CHAT_TYPES.get(chat.response_type, chat.response_type),
                       'type': chat.response_type, 'message': chat.message, 'response': chat.response}
                      for chat in unhelpful],
    }


def _term_fill(term):
    """How full a term's lessons are, overall and per category.

    Uses the Lesson Enrollments report's rule: a lesson is running in a term if
    it is active or has swimmers in it, and only running lessons count places.
    """
    from lessons.models import Product
    from lessons_bookings.models import LessonEnrollment

    counts = dict(LessonEnrollment.objects.filter(term=term)
                  .values_list('lesson_id').annotate(n=Count('id')))
    lessons = (Product.objects.filter(active=True) | Product.objects.filter(id__in=list(counts)))
    lessons = lessons.select_related('category').distinct()

    enrolled_total = places_total = full = nearly_full = 0
    categories = defaultdict(lambda: {'enrolled': 0, 'places': 0})
    for lesson in lessons:
        enrolled = counts.get(lesson.id, 0)
        if not (lesson.active or enrolled):
            continue
        places = lesson.num_places or 0
        enrolled_total += enrolled
        places_total += places
        category = categories[lesson.category.short_name or lesson.category.name]
        category['enrolled'] += enrolled
        category['places'] += places
        pct = _fill_pct(enrolled, places)
        if pct is not None and pct >= 100:
            full += 1
        elif pct is not None and pct >= NEARLY_FULL_PCT:
            nearly_full += 1

    by_category = sorted(
        ({'name': name, **c, 'pct': _fill_pct(c['enrolled'], c['places'])}
         for name, c in categories.items() if c['places']),
        key=lambda c: -c['pct'],
    )
    return {
        'enrolled': enrolled_total,
        'places': places_total,
        'pct': _fill_pct(enrolled_total, places_total),
        'categories': by_category,
        'full': full,
        'nearly_full': nearly_full,
    }


def _daily_series(queryset, field, days, amount=None):
    """Per local day over ``days``: row counts, or the sum of ``amount``."""
    start = make_aware(datetime.datetime.combine(days[0], datetime.time.min))
    totals = defaultdict(int)
    columns = [field, amount] if amount else [field]
    for row in queryset.filter(**{f'{field}__gte': start}).values_list(*columns):
        day = localtime(row[0]).date()
        totals[day] += (row[1] or 0) if amount else 1
    return [totals[day] for day in days]


DIAL_ARC_LENGTH = 282.74  # the dial's semicircle: pi * radius 90


def _dial(title, value, maximum, caption, empty='No data yet', target=None, target_label=''):
    """One half-circle gauge. The needle stops at full; the label shows the real %.

    ``target`` is a percentage to mark on the ring, e.g. last term's fill.
    """
    pct = _fill_pct(value, maximum)
    shown = min(pct or 0, 100)
    if pct is None:
        level = 'none'
    elif pct >= NEARLY_FULL_PCT:
        level = 'high'
    elif pct >= 50:
        level = 'mid'
    else:
        level = 'low'
    return {
        'title': title,
        'value': value,
        'max': maximum,
        'pct': pct,
        'level': level,
        'angle': round(-90 + 1.8 * shown, 1),
        'arc': round(DIAL_ARC_LENGTH * shown / 100, 2),
        'caption': caption,
        'empty': empty,
        'target': target,
        'target_label': target_label,
        'target_angle': None if target is None else round(-90 + 1.8 * min(target, 100), 1),
    }


def _live_dials(today):
    """The dashboard's dials, keyed so a page can show just some of them.

    Each is a dial, or None when it does not apply (no current or next term).
    Also returns the current term and its fill, which the dashboard reuses.
    """
    from anseo.models import AttendanceEntry
    from lessons_bookings.models import LessonEnrollment, Term
    from swims.models import PublicSwimProduct
    from swims_orders.models import OrderItem as SwimOrderItem

    today_period, _, week_period = _activity_periods(today)
    live = {'term': None, 'registers': None, 'next_term': None}

    current_term = Term.get_current_term()
    this_fill = _term_fill(current_term) if current_term else None
    if this_fill:
        # Marked with last term's fill. Its places are counted the same way, so a
        # lesson added since counts against last term too.
        previous_term = Term.get_previous_term()
        last_pct = _term_fill(previous_term)['pct'] if previous_term else None
        live['term'] = _dial('This term’s lessons', this_fill['enrolled'], this_fill['places'],
                             'places filled', target=last_pct,
                             target_label=f'Last term: {last_pct}%' if last_pct is not None else '')

    swim_places = (PublicSwimProduct.objects.filter(available=True, day_of_week=today.weekday())
                   .aggregate(n=Sum('num_places'))['n'] or 0)
    swimmers_booked = (SwimOrderItem.objects.filter(order__paid=True, order__booking=today)
                       .exclude(order__payment_status='refunded')
                       .aggregate(n=Sum('quantity'))['n'] or 0)
    live['swims'] = _dial('Today’s public swims', swimmers_booked, swim_places,
                          'swim places paid for', empty='No public swims today')

    # A register is dated when it is marked, not by the class it is for (see
    # AttendanceRoll.get_or_create_current), so a catch-up on Sunday counts on Sunday.
    # Swimmers left as Not Marked count too, so a half-done register shows.
    marked_entries = AttendanceEntry.objects.exclude(status=AttendanceEntry.UNKNOWN)
    on_today = AttendanceEntry.objects.filter(roll__window_start__gte=today_period[1],
                                              roll__window_start__lt=today_period[2])
    attended = on_today.filter(status__in=[AttendanceEntry.PRESENT, AttendanceEntry.LATE]).count()
    unmarked = on_today.filter(status=AttendanceEntry.UNKNOWN).count()
    live['attendance'] = _dial('Swimmers’ attendance today', attended, on_today.count(),
                               f'present or late · {unmarked} not marked',
                               empty='No registers marked yet today')

    if current_term:
        # Lessons with swimmers whose class day has come round so far this week.
        due = set(LessonEnrollment.objects
                  .filter(term=current_term, lesson__day_of_week__lte=today.weekday())
                  .values_list('lesson_id', flat=True))
        taken = set(marked_entries
                    .filter(roll__product_id__in=due, roll__window_start__gte=week_period[1],
                            roll__window_start__lt=week_period[2])
                    .values_list('roll__product_id', flat=True))
        live['registers'] = _dial('Classes’ attendance recorded this week', len(taken), len(due),
                                  'classes so far', empty='No classes yet this week')

    next_term = Term.get_next_term()
    if next_term:
        next_fill = _term_fill(next_term)
        live['next_term'] = _dial('Next term booked', next_fill['enrolled'], next_fill['places'],
                                  f'places booked · starts {next_term.start_date.day} {next_term.start_date:%b}')

    # Two-factor: an authenticator app counts; recovery codes alone come with one anyway.
    from allauth.mfa.models import Authenticator
    from django.contrib.auth import get_user_model

    active = get_user_model().objects.filter(is_active=True)
    with_app = set(Authenticator.objects.filter(type=Authenticator.Type.TOTP).values_list('user_id', flat=True))
    staff_ids = set(active.filter(is_staff=True).values_list('id', flat=True))
    guardian_ids = set(active.filter(is_staff=False, swimling__isnull=False).values_list('id', flat=True))
    live['staff_2fa'] = _dial('Staff with 2FA', len(staff_ids & with_app), len(staff_ids),
                              'active staff accounts')
    live['guardian_2fa'] = _dial('Guardians with 2FA', len(guardian_ids & with_app), len(guardian_ids),
                                 'accounts with a swimmer', empty='No guardian accounts')

    # Confirmed email, counted as users.adapters.email_confirmed counts it: a verified
    # address, or Google having verified the same one (recorded only once they next
    # load a page, so counted here from Google's own data too).
    from allauth.account.models import EmailAddress
    from allauth.socialaccount.models import SocialAccount
    from users.adapters import google_verified_email

    confirmed = set(EmailAddress.objects.filter(user_id__in=guardian_ids, verified=True,
                                                email__iexact=F('user__email'))
                    .values_list('user_id', flat=True))
    for account in SocialAccount.objects.filter(user_id__in=guardian_ids, provider='google').select_related('user'):
        if google_verified_email(account) == account.user.email.lower():
            confirmed.add(account.user_id)
    live['guardian_email'] = _dial('Guardians with confirmed email', len(confirmed), len(guardian_ids),
                                   'accounts with a swimmer', empty='No guardian accounts')

    funnel = _checkout_funnel(week_period[1], week_period[2])
    live['checkouts'] = _dial('Checkouts finished this week', funnel['finished'], funnel['started'],
                              f"families who reached payment · {funnel['retried']} needed more than "
                              f"one try · {funnel['left']} left", empty='No checkouts yet this week')

    live.update(current_term=current_term, this_fill=this_fill)
    return live


def _whats_on(today):
    """Today's timetable in brief: public swims, lessons and school classes.

    Read from the timetable alone. Nothing records closures or bank holidays, so on
    a day the pool is shut the usual classes still show; the page says "as timetabled".
    """
    from django.urls import reverse
    from instructors.models import InstructorAssignment
    from lessons.models import Product
    from lessons_bookings.models import LessonAssignment, LessonEnrollment, Term
    from schools.models import ScoLessons
    from schools_bookings.models import ScoEnrollment, ScoTerm
    from swims.models import PublicSwimProduct
    from swims_orders.models import OrderItem as SwimOrderItem

    weekday = today.weekday()

    # Paid swimmers per session, counted as the swims dial counts them.
    booked = dict(SwimOrderItem.objects.filter(order__paid=True, order__booking=today)
                  .exclude(order__payment_status='refunded')
                  .order_by().values_list('order__product_id').annotate(n=Sum('quantity')))
    swims = [
        {'start': swim.start_time, 'end': swim.end_time, 'name': swim.category.name,
         'booked': booked.get(swim.id, 0), 'places': swim.num_places or 0}
        for swim in (PublicSwimProduct.objects.filter(available=True, day_of_week=weekday)
                     .select_related('category').order_by('start_time'))
    ]

    # Lessons: one line, as there are a couple of dozen classes on a weekday.
    lessons = None
    term = Term.get_current_term()
    if term:
        swimmers = dict(LessonEnrollment.objects.filter(term=term, lesson__day_of_week=weekday)
                        .order_by().values_list('lesson_id').annotate(n=Count('id')))
        if swimmers:
            times = Product.objects.filter(id__in=swimmers).values_list('start_time', 'end_time')
            # Instructors are assigned through either model; see instructors.utils.
            taught = set(InstructorAssignment.objects.filter(term=term, lesson_id__in=swimmers)
                         .values_list('lesson_id', flat=True))
            taught |= set(LessonAssignment.objects.filter(term=term, lessons__in=swimmers)
                          .values_list('lessons', flat=True))
            unstaffed = (Product.objects.filter(id__in=set(swimmers) - taught)
                         .select_related('category').order_by('start_time'))
            lessons = {
                'classes': len(swimmers),
                'swimmers': sum(swimmers.values()),
                'start': min(start for start, _ in times),
                'end': max(end for _, end in times),
                'unstaffed': [{'start': lesson.start_time, 'end': lesson.end_time,
                               'name': lesson.category.name,
                               'swimmers': swimmers[lesson.id]} for lesson in unstaffed],
                'url': f"{reverse('dashboard:admin_lessons_list')}?day={weekday}",
            }

    # School classes with swimmers in a term that is running today.
    school_terms = ScoTerm.objects.filter(start_date__lte=today, end_date__gte=today)
    school_swimmers = dict(ScoEnrollment.objects.filter(term__in=school_terms, lesson__day_of_week=weekday)
                           .order_by().values_list('lesson_id').annotate(n=Count('id')))
    schools = [
        {'start': lesson.start_time, 'end': lesson.end_time,
         'name': lesson.school.name if lesson.school else str(lesson.category),
         'swimmers': school_swimmers[lesson.id]}
        for lesson in (ScoLessons.objects.filter(id__in=school_swimmers)
                       .select_related('school', 'category').order_by('start_time'))
    ]

    return {'swims': swims, 'lessons': lessons, 'schools': schools, 'no_term': term is None,
            'empty': not (swims or lessons or schools)}


@staff_member_required
def live_dashboard(request, template_name='admin/financeadmin/dashboard.html'):
    """Live numbers for today and this week, as dials, tiles and charts."""
    from django.contrib.auth import get_user_model
    from django.urls import reverse
    from anseo.models import AttendanceEntry
    from chatbot.models import ChatbotQuery
    from custom_admins.financeadmin import finance_admin_site
    from custom_admins.panels import settings_site
    from lessons_bookings.models import LessonEnrollment, Term
    from schools_bookings.models import ScoEnrollment
    from swims.models import PublicSwimProduct
    from swims_orders.models import OrderItem as SwimOrderItem
    from users.models import ActiveDay, LoginEvent
    from waiting_list.models import WaitingList

    User = get_user_model()
    today = localtime(now()).date()
    today_period, _, week_period = _activity_periods(today)
    periods = [today_period, week_period]  # tiles show today and this week

    # --- Dials -------------------------------------------------------------
    live = _live_dials(today)
    current_term, this_fill = live['current_term'], live['this_fill']
    dials = [live[key] for key in ('term', 'checkouts', 'swims', 'attendance', 'registers', 'next_term',
                                   'staff_2fa', 'guardian_2fa', 'guardian_email') if live[key]]

    # --- Tiles -------------------------------------------------------------
    order_rows = [_paid_orders(model, periods) for model, _ in ORDER_MODELS.values()]
    customers = {'user__is_staff': False}
    staff = {'user__is_staff': True}
    managers = {'user__is_staff': True, 'user__groups__name': 'Manager'}

    def tile(label, values, money=False, hint=''):
        return {'label': label, 'today': values[0], 'week': values[1], 'money': money, 'hint': hint}

    tiles = [
        tile('Revenue', [sum(col) for col in zip(*(r[1] for r in order_rows))], money=True,
             hint='Refunds left out'),
        tile('Paid orders', [sum(col) for col in zip(*(r[0] for r in order_rows))]),
        tile('New customers', _period_counts(User.objects.filter(is_staff=False), periods, 'date_joined')),
        tile('New guardians', _period_counts(User.objects.filter(is_staff=False, swimling__isnull=False).distinct(),
                                             periods, 'date_joined'),
             hint='New customers who have added a swimmer'),
        tile('Customers logged in', _period_counts(LoginEvent.objects.filter(**customers), periods,
                                                   distinct='user')),
        tile('Customers active', _period_counts(ActiveDay.objects.filter(**customers), periods, 'date',
                                                distinct='user'), hint='Used the site while logged in'),
        tile('Managers active', _period_counts(ActiveDay.objects.filter(**managers), periods, 'date',
                                               distinct='user'), hint='Used the site while logged in'),
        tile('Other staff active', _period_counts(ActiveDay.objects.filter(**staff).exclude(**managers), periods,
                                                  'date', distinct='user')),
        tile('New enrolments', [a + b for a, b in zip(
            _period_counts(LessonEnrollment.objects.all(), periods),
            _period_counts(ScoEnrollment.objects.all(), periods))], hint='Lessons and schools'),
        tile('Swim check-ins', _period_counts(Order.objects.all(), periods, 'checked_in_at')),
        tile('Joined waiting list', _period_counts(WaitingList.objects.all(), periods, 'created_at'),
             hint=f'{WaitingList.objects.filter(completed=False).count()} waiting now'),
    ]

    chats = ChatbotQuery.objects.all()
    week_chats =dict(chats.filter(timestamp__gte=week_period[1], timestamp__lt=week_period[2])
                      .values_list('response_type').annotate(n=Count('id')))
    tiles.append(tile(
        'AI chat questions', _period_counts(chats, periods, 'timestamp'),
        hint=(f"This week: {week_chats.get('GPT', 0)} by the AI model, "
              f"{week_chats.get('FAQ', 0) + week_chats.get('FAQ_HEDGED', 0)} from the FAQ"),
    ))
    chat_summary = _chat_summary(chats)
    recent_chats = [
        {
            'when': chat.timestamp,
            'kind': CHAT_TYPES.get(chat.response_type, chat.response_type),
            'type': chat.response_type,
            # Blocked messages are abusive by definition; the full text is in the admin.
            'message': '' if chat.response_type == 'BLOCKED' else chat.message,
            'lessons': chat.source == 'public_lesson',
            'customer': bool(chat.user_id),
            'rating': chat.rating,
        }
        for chat in chats.order_by('-timestamp')[:RECENT_CHAT_QUESTIONS]
    ]
    chat_ratings = _chat_ratings(chats, today)

    # --- Charts ------------------------------------------------------------
    days = [today - timedelta(days=n) for n in range(DASHBOARD_DAYS - 1, -1, -1)]
    logins = LoginEvent.objects.all()
    chart_data = {
        'days': [f'{day:%a} {day.day}' for day in days],
        'customer_logins': _daily_series(logins.filter(**customers), 'created', days),
        'staff_logins': _daily_series(logins.filter(**staff), 'created', days),
        'signups': _daily_series(User.objects.filter(is_staff=False), 'date_joined', days),
        'revenue': {
            label: [float(v) for v in _daily_series(
                model.objects.filter(paid=True).exclude(payment_status='refunded'), 'created', days, 'amount')]
            for model, label in ORDER_MODELS.values()
        },
        'categories': this_fill['categories'] if this_fill else [],
        'chats': {
            label: _daily_series(chats.filter(response_type=key), 'timestamp', days)
            for key, label in CHAT_TYPES.items()
        },
    }

    context = {
        **finance_admin_site.each_context(request),
        'title': 'Live Dashboard',
        'today': today,
        'week_start': week_period[1],
        'dials': dials,
        'whats_on': _whats_on(today),
        'tiles': tiles,
        'term': current_term,
        'term_fill': this_fill,
        'recent_chats': recent_chats,
        'chat_summary': chat_summary,
        'chat_ratings': chat_ratings,
        # The chat log lives in Settings, which Full-Timers cannot open.
        'chat_log_url': (reverse('settings:chatbot_chatbotquery_changelist')
                         if settings_site.has_permission(request) else None),
        'chart_data': chart_data,
    }
    return render(request, template_name, context)
