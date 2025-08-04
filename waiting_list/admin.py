from django.contrib import admin
from django.utils import timezone
from .models import WaitingList
from lessons.models import Product
from django.contrib import admin
from django.utils import timezone
from .models import WaitingList
from lessons_bookings.models import LessonEnrollment, Term


@admin.register(WaitingList)
class WaitingListAdmin(admin.ModelAdmin):
    list_display = (
        'swimling', 'product', 'get_guardian', 'is_transfer_request',
        'has_enrolled_sibling', 'is_notified', 'assigned_lesson', 'completed', 'created_at'
    )
    list_filter = ('is_notified', 'is_transfer_request', 'created_at')
    search_fields = (
        'swimling__first_name', 'swimling__last_name', 'product__name', 'swimling__guardian__username'
    )

    def get_guardian(self, obj):
        return obj.swimling.guardian
    get_guardian.short_description = "Guardian"
    get_guardian.admin_order_field = 'swimling__guardian'

    def has_enrolled_sibling(self, obj):
        current_term_id = Term.get_current_term_id()
        if not current_term_id:
            return False

        return LessonEnrollment.objects.filter(
            swimling__guardian=obj.swimling.guardian,
            term_id=current_term_id
        ).exclude(
            swimling=obj.swimling
        ).exists()
    has_enrolled_sibling.short_description = "Sibling Enrolled"
    has_enrolled_sibling.boolean = True  # ✅ shows