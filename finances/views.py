from django.db.models import Sum
from django.utils.timezone import now, timedelta
from django.shortcuts import render
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse
from django.utils.timezone import localtime
from swims_orders.models import Order  # ✅ your Order model


@staff_member_required
def transactions_data(request):
    """
    Return JSON for DataTables with Swim Orders
    """
    data = []
    orders = Order.objects.select_related("user", "product", "coupon").order_by("-created")[:500]

    for o in orders:
        data.append({
            "date": localtime(o.created).strftime("%Y-%m-%d %H:%M"),
            "guardian": getattr(o.user, "email", str(o.user)),  # or .get_full_name()
            "amount": float(o.amount),
            "discount": float(o.discount_amount or 0),
            "coupon": o.coupon.code if o.coupon else "",
            "product": o.product.name if o.product else "",
            "status": "Paid" if o.paid else "Unpaid",
            "tx_id": o.txId,
            "payment_status": o.payment_status,
        })

    return JsonResponse({"data": data})


@staff_member_required
def dashboard(request):
    today = now().date()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    # Revenue summaries (only count paid orders)
    today_rev = Order.objects.filter(paid=True, created__date=today).aggregate(Sum("amount"))["amount__sum"] or 0
    week_rev = Order.objects.filter(paid=True, created__date__gte=week_start).aggregate(Sum("amount"))["amount__sum"] or 0
    month_rev = Order.objects.filter(paid=True, created__date__gte=month_start).aggregate(Sum("amount"))["amount__sum"] or 0

    context = {
        "today_rev": today_rev,
        "week_rev": week_rev,
        "month_rev": month_rev,
    }
    return render(request, "finances/dashboard.html", context)
