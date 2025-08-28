from django.shortcuts import render, get_object_or_404
from django.views.generic import ListView
from .models import Coupon

class CouponListView(ListView):
    model = Coupon
    template_name = "coupons/templates/coupon_list.html"
    context_object_name = "coupons"

    def get_queryset(self):
        return Coupon.objects.filter(active=True).order_by("-created_at")


def coupon_detail(request, code):
    coupon = get_object_or_404(Coupon, code=code)
    return render(request, "coupons/templates/coupon_detail.html", {"coupon": coupon})