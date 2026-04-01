from collections import defaultdict
from decimal import Decimal

from django.db.models import Sum, Count
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


@staff_member_required
def transactions_data(request):
    """
    Return JSON for DataTables with optional period filter
    """
    data = []
    orders = Order.objects.select_related("user", "product", "coupon")

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
def revenue_report(request):
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
    }
    return render(request, 'finances/revenue_report.html', context)


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

ORDER_MODELS = {
    'lesson': (LessonOrder, 'Lesson'),
    'swim': (Order, 'Swim'),
    'school': (SchoolOrder, 'School'),
}


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
            elif not notifications:
                category = 'missing_notification'
                notif_amount = None
                difference = None
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
def reconciliation_dashboard(request):
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
    return render(request, 'finances/reconciliation.html', context)


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


@staff_member_required
def reconciliation_verify(request, order_type, order_id):
    """Verify a single order with BOIPA API and return updated row."""
    from boipa.utils import verify_boipa_transaction
    from django.views.decorators.http import require_POST

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
    if tx_id:
        verified = verify_boipa_transaction(tx_id)
        order.boipa_reconciled = verified
        order.save(update_fields=['boipa_reconciled'])

    # Rebuild classification for this single order
    notifications = list(order.notifications.all())
    if not tx_id:
        cat = 'no_txid'
        notif_amount = None
        difference = None
    elif not notifications:
        cat = 'missing_notification'
        notif_amount = None
        difference = None
    else:
        captured = [n for n in notifications if (n.status or '').upper() == 'CAPTURED']
        best = captured[0] if captured else notifications[0]
        notif_amount = best.amount
        if notif_amount is not None and notif_amount == order.amount:
            cat = 'matched'
            difference = Decimal('0')
        else:
            cat = 'mismatched'
            difference = (order.amount - notif_amount) if notif_amount is not None else None

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
    }
    return render(request, 'finances/partials/reconciliation_row.html', {'row': row})


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