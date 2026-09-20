from django.contrib import admin  # ✅ Needed for admin.StackedInline, admin.ModelAdmin
from django.contrib.admin import AdminSite
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin

from import_export.admin import ImportExportMixin, ImportExportModelAdmin
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter

from django.urls import reverse
from django.utils.html import format_html

from hijack.contrib.admin import HijackUserAdminMixin

from django.contrib import messages
from django.contrib.auth.tokens import default_token_generator
from django.utils.http import urlsafe_base64_encode
from django.utils.encoding import force_bytes
from django.core.mail import send_mail
from django.conf import settings

from users.models import Swimling
from users.resources import SwimlingResource, UserResource, GroupResource
from lessons_bookings.models import LessonEnrollment, Term
from lessons.models import Product

from custom_admins.base import TCSPModelAdmin
from custom_admins.panels import operations_site, settings_site






User = get_user_model()


# 🔹 Admin site


# Panel consolidation: this name now points at the shared panel.
users_admin_site = settings_site
# 🔹 Inlines
class SwimlingInline(admin.StackedInline):
    model = Swimling
    extra = 1
    fields = ('first_name', 'last_name', 'dob', 'sco_role_num', 'notes')


# 🔹 LessonEnrollment Inline for Swimling detail
class LessonEnrollmentInline(admin.TabularInline):
    model = LessonEnrollment
    extra = 0
    fields = ('lesson', 'term', 'order', 'created')
    readonly_fields = ('created',)
    autocomplete_fields = ['lesson', 'term']


# 🔹 Swimling Admin
class SwimlingAdmin(ImportExportMixin, TCSPModelAdmin):
    # Walked by guardian_link, which list_display cannot reveal.
    list_select_related_extra = ("guardian",)

    resource_class = SwimlingResource
    inlines = [LessonEnrollmentInline]
    list_display = ['first_name', 'last_name', 'guardian_link']
    list_filter = [
        ('last_name', DropdownFilter),
        ('first_name', DropdownFilter),
        ('guardian', RelatedDropdownFilter),
    ]
    search_fields = ['first_name', 'last_name', 'guardian__email', 'guardian__first_name', 'guardian__last_name']
    ordering = ['guardian__last_name', 'last_name']

    def guardian_link(self, obj):
        if obj.guardian:
            try:
                # Operations carries a read-only guardian view; Managers get the
                # editable one on Settings.
                url = reverse(
                    "operations:%s_%s_change" % (
                        obj.guardian._meta.app_label,
                        obj.guardian._meta.model_name
                    ),
                    args=[obj.guardian.pk]
                )
                # 👇 Prefer full name, but fallback to email or __str__
                name = (f"{obj.guardian.first_name} {obj.guardian.last_name}".strip()
                        or obj.guardian.email
                        or str(obj.guardian))
                return format_html('<a href="{}">{}</a>', url, name)
            except Exception:
                return str(obj.guardian)
        return "-"

    guardian_link.short_description = 'Guardian'


# 🔹 Admin action: Send password reset email
@admin.action(description="📩 Send password reset email")
def send_password_reset_email(modeladmin, request, queryset):
    for user in queryset:
        if not user.email:
            messages.warning(request, f"⚠️ User {user} has no email address.")
            continue

        token = default_token_generator.make_token(user)
        uid = urlsafe_base64_encode(force_bytes(user.pk))
        reset_path = reverse('password_reset_confirm', kwargs={'uidb64': uid, 'token': token})

        # ✅ Build full URL using request context
        scheme = request.scheme
        domain = request.get_host()
        full_url = f"{scheme}://{domain}{reset_path}"

        send_mail(
            subject="🔐 Reset your password",
            message=(
                f"Hi {user.get_full_name() or user.email},\n\n"
                f"You requested to reset your password.\n\n"
                f"Click the link below to set a new password:\n{full_url}\n\n"
                f"If you didn’t request this, please ignore this email."
            ),
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[user.email],
            fail_silently=False,
        )

        messages.success(request, f"✅ Password reset email sent to {user.email}")

# 🔹 User Admin
class UserAdmin(HijackUserAdminMixin, ImportExportMixin, BaseUserAdmin):
    resource_class = UserResource
    list_per_page = 20
    inlines = [SwimlingInline]

    fieldsets = (
        (None, {'fields': ('email', 'password', 'mobile_phone', 'first_name', 'last_name', 'admin_notes', 'last_login')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Groups and Permissions', {'fields': ('groups', 'user_permissions')})
    )

    readonly_fields = ('user_permissions',)
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')
        }),
    )

    def get_user_id(self, obj):
        return obj.id
    get_user_id.short_description = 'User ID'

    def display_groups(self, obj):
        return ', '.join([group.name for group in obj.groups.all()])
    display_groups.short_description = 'Groups'

    list_display = ('get_user_id', 'email', 'username', 'mobile_phone', 'display_groups')
    list_filter = [
        ('last_name', DropdownFilter),
        ('first_name', DropdownFilter),
        ('groups', RelatedDropdownFilter),
    ]
    search_fields = ('email', 'last_name', 'first_name')
    ordering = ('last_name', 'first_name')
    filter_horizontal = ('groups',)

    # 🔹 Register the password reset action
    actions = [send_password_reset_email]


# 🔹 Group Admin
class GroupAdmin(BaseGroupAdmin, ImportExportModelAdmin, TCSPModelAdmin):
    resource_class = GroupResource


# 🔹 Register with default admin (for Hijack compatibility)
try:
    admin.site.register(User, UserAdmin)
except admin.sites.AlreadyRegistered:
    pass

# 🔹 Autocomplete support for Product and Term (powers autocomplete_fields in inlines)
class ProductAutocompleteAdmin(TCSPModelAdmin):
    search_fields = ['name']
    def has_module_permission(self, request):
        return False

class TermAutocompleteAdmin(TCSPModelAdmin):
    search_fields = ['id']
    def has_module_permission(self, request):
        return False

# 🔹 Guardian lookup for the Operations panel.
#
# Desk staff answer the phone and need a parent's number, but editing users —
# and with it staff status and group membership — belongs on Settings with the
# Managers. So the same model is registered twice: fully on Settings, and
# read-only here.
class GuardianLookupAdmin(TCSPModelAdmin):
    """Read-only view of a guardian and their swimmers."""

    list_display = ("full_name", "email", "mobile_phone", "swimling_names")
    search_fields = ("email", "first_name", "last_name", "mobile_phone")
    list_filter = ("is_active",)
    ordering = ("last_name", "first_name")
    inlines = [SwimlingInline]

    def get_queryset(self, request):
        # Guardians only — the swimmer-less accounts are staff and customers.
        return super().get_queryset(request).prefetch_related("swimling_set")

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name or ''}".strip() or obj.email
    full_name.short_description = "Name"
    full_name.admin_order_field = "last_name"

    def swimling_names(self, obj):
        names = [f"{s.first_name} {s.last_name or ''}".strip() for s in obj.swimling_set.all()]
        return ", ".join(names) if names else "—"
    swimling_names.short_description = "Swimmers"

    # Reaching the Operations panel at all already required is_staff and passing
    # the panel's own check, so viewing is granted here rather than depending on
    # per-model Django permissions, which desk accounts do not carry.
    def has_view_permission(self, request, obj=None):
        return request.user.is_active and request.user.is_staff

    def has_module_permission(self, request):
        return self.has_view_permission(request)

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


# 🔹 Register all
users_admin_site.register(User, UserAdmin)
operations_site.register(User, GuardianLookupAdmin)
operations_site.register(Swimling, SwimlingAdmin)
users_admin_site.register(Group, GroupAdmin)
users_admin_site.register(Product, ProductAutocompleteAdmin)
users_admin_site.register(Term, TermAutocompleteAdmin)
