from django.db.models.signals import post_save
from django.dispatch import receiver

from lessons_orders.models import Order as LessonOrder
from schools_orders.models import Order as SchoolOrder

from .services import confirm_pending_redemptions


@receiver(post_save, sender=LessonOrder)
@receiver(post_save, sender=SchoolOrder)
def confirm_coupons_when_paid(sender, instance, **kwargs):
    # Every route that marks an order paid — BOIPA's return page and webhook,
    # zero-balance checkouts, staff in the admin — saves it, so confirming here
    # covers them all. Does nothing once the order's coupons are confirmed.
    if instance.paid:
        confirm_pending_redemptions(instance)
