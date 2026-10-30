from django.contrib.admin.views.decorators import staff_member_required
from django.shortcuts import render, get_object_or_404
from django.utils.decorators import method_decorator
from django.views.generic import ListView
from .models import Coupon

# Staff only: these show live coupon codes, balances and who they belong to.
@method_decorator(staff_member_required, name="dispatch")
class CouponListView(ListView):
    model = Coupon
    template_name = "coupons/coupon_list.html"
    context_object_name = "coupons"

    def get_queryset(self):
        return Coupon.objects.filter(active=True).order_by("-created_at")


@staff_member_required
def coupon_detail(request, code):
    coupon = get_object_or_404(Coupon, code=code)
    return render(request, "coupons/coupon_detail.html", {"coupon": coupon})