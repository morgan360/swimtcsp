from django.db.models import Sum
from django.utils.timezone import now, timedelta
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils.timezone import localtime
from swims_orders.models import Order  # ✅ your Order model
from django.utils.timezone import localtime, make_aware
import datetime


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