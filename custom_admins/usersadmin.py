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
from django.utils import timezone

from finances.models import DashboardOpen
from users.models import ActiveDay, DataRetentionEvent, LoginEvent, Swimling
from users.resources import SwimlingResource, UserResource, GroupResource
from lessons_bookings.models import LessonEnrollment, Term
from lessons.models import Product

from custom_admins.base import TCSPModelAdmin
from utils.admin_filters import SearchableRelatedDropdownFilter
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


class RetentionStatusFilter(admin.SimpleListFilter):
    """Show current accounts unless asked, as promised to Esther and Brian.

    Archived accounts are one click away ("Archived" or "All") for when a
    lapsed family rings up to come back; anonymised ones are rows with no name.
    """
    title = "account status"
    parameter_name = "retention"
    lookup = "anonymised_at"  # overridden for Swimling

    def lookups(self, request, model_admin):
        return [
            ("current", "Current"),
            ("archived", "Archived (3+ years quiet)"),
            ("anonymised", "Anonymised"),
            ("all", "All"),
        ]

    def choices(self, changelist):
        # "current" is the default, so the built-in "All" link would lie.
        for value, label in self.lookup_choices:
            yield {
                "selected": (self.value() or "current") == value,
                "query_string": changelist.get_query_string({self.parameter_name: value}),
                "display": label,
            }

    def queryset(self, request, queryset):
        prefix = self.lookup.removesuffix("anonymised_at")
        value = self.value() or "current"
        if value == "current":
            return queryset.filter(**{f"{prefix}archived_at__isnull": True, f"{prefix}anonymised_at__isnull": True})
        if value == "archived":
            return queryset.filter(**{f"{prefix}archived_at__isnull": False, f"{prefix}anonymised_at__isnull": True})
        if value == "anonymised":
            return queryset.filter(**{f"{prefix}anonymised_at__isnull": False})
        return queryset


class SwimlingRetentionStatusFilter(RetentionStatusFilter):
    lookup = "guardian__anonymised_at"


# 🔹 Swimling Admin
class SwimlingAdmin(ImportExportMixin, TCSPModelAdmin):
    # Walked by guardian_link, which list_display cannot reveal.
    list_select_related_extra = ("guardian",)

    resource_class = SwimlingResource
    inlines = [LessonEnrollmentInline]
    list_display = ['first_name', 'last_name', 'guardian_link']
    list_filter = [
        SwimlingRetentionStatusFilter,
        ('guardian', SearchableRelatedDropdownFilter),
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

# 🔹 Admin action: Reset two-factor authentication
@admin.action(description="🔓 Reset two-factor authentication")
def reset_two_factor(modeladmin, request, queryset):
    """Remove a user's authenticator app and recovery codes.

    For someone who has lost their phone and their recovery codes. They sign in
    with their password alone next time and, if staff, are asked to set two-factor
    up again straight away. Only a superuser may reset a staff account, so one
    compromised staff password cannot strip another account's second factor.
    """
    from allauth.mfa.models import Authenticator

    for user in queryset:
        if user.is_staff and not request.user.is_superuser:
            messages.error(request, f"Only a superuser can reset two-factor for staff account {user.email}.")
            continue
        deleted, _ = Authenticator.objects.filter(user=user).delete()
        if deleted:
            messages.success(request, f"Two-factor authentication reset for {user.email}.")
        else:
            messages.info(request, f"{user.email} did not have two-factor authentication set up.")


@admin.action(description="🗑️ Erase personal data (GDPR request)")
def erase_personal_data(modeladmin, request, queryset):
    """A parent has asked to be forgotten. Superusers only, and confirmed first.

    Anonymises the account and every swimmer on it at once and deletes them from
    Mailchimp. Order rows stay, so payments still reconcile. Cannot be undone.
    """
    from django.template.response import TemplateResponse
    from users.retention import erase_user

    if not request.user.is_superuser:
        messages.error(request, "Only a superuser can erase an account.")
        return None
    staff = [u for u in queryset if u.is_staff or u.is_superuser]
    if staff:
        messages.error(request, "Staff accounts cannot be erased here: " + ", ".join(u.email for u in staff))
        return None

    if request.POST.get("confirm_erase") == "yes":
        for user in queryset:
            result = erase_user(user, performed_by=request.user)
            if result.cleared.get("mailchimp") == "failed":
                messages.warning(request, f"Account {user.pk} erased, but Mailchimp could not be reached: "
                                          "remove the contact there by hand.")
            else:
                messages.success(request, f"Account {user.pk} erased.")
        return None

    today = timezone.localdate()
    rows = []
    for user in queryset.prefetch_related("swimling_set"):
        upcoming = LessonEnrollment.objects.filter(swimling__guardian=user, term__end_date__gte=today).count()
        rows.append({"user": user, "swimlings": list(user.swimling_set.all()), "upcoming": upcoming})
    return TemplateResponse(request, "admin/users/erase_confirm.html", {
        **modeladmin.admin_site.each_context(request),
        "title": "Erase personal data",
        "rows": rows,
        "queryset": queryset,
        "action_checkbox_name": admin.helpers.ACTION_CHECKBOX_NAME,
        "opts": modeladmin.model._meta,
    })


# 🔹 User Admin
class UserAdmin(HijackUserAdminMixin, ImportExportMixin, BaseUserAdmin):
    resource_class = UserResource
    list_per_page = 20
    inlines = [SwimlingInline]

    fieldsets = (
        (None, {'fields': ('email', 'password', 'mobile_phone', 'first_name', 'last_name', 'admin_notes', 'last_login')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Groups and Permissions', {'fields': ('groups', 'user_permissions')}),
        ('News and data retention', {'fields': ('marketing_opt_in', 'marketing_opt_in_at', 'archived_at', 'anonymised_at')}),
    )

    readonly_fields = ('user_permissions', 'marketing_opt_in_at', 'archived_at', 'anonymised_at')

    def get_readonly_fields(self, request, obj=None):
        """Only superusers may grant staff or superuser status.

        These fields were editable by anyone who could reach this page, which
        made the user admin a privilege-escalation route.
        """
        fields = list(super().get_readonly_fields(request, obj))
        if not request.user.is_superuser:
            fields += ["is_staff", "is_superuser", "groups"]
        return fields
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

    def get_queryset(self, request):
        # display_groups walks a m2m, so prefetch rather than one query per row.
        return super().get_queryset(request).prefetch_related('groups')
    list_filter = [
        RetentionStatusFilter,
        ('groups', RelatedDropdownFilter),
        'is_active',
        'is_staff',
        'marketing_opt_in',
    ]
    search_fields = ('email', 'last_name', 'first_name')
    ordering = ('last_name', 'first_name')
    filter_horizontal = ('groups',)

    # 🔹 Register the password reset action
    actions = [send_password_reset_email, reset_two_factor, erase_personal_data]


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
#
# Hijack lives here too, not only on Settings: every staff member logs in as a
# parent to see what they see. HIJACK_PERMISSION_CHECK still decides each row,
# so staff get the button on customers only, never on other staff.
class GuardianLookupAdmin(HijackUserAdminMixin, TCSPModelAdmin):
    """Read-only view of a guardian and their swimmers."""

    list_display = ("full_name", "email", "mobile_phone", "swimling_names")
    search_fields = ("email", "first_name", "last_name", "mobile_phone")
    list_filter = (RetentionStatusFilter, "is_active")
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


class LoginEventAdmin(TCSPModelAdmin):
    """Read-only log of logins, written by the user_logged_in signal."""
    list_display = ("created", "user", "is_staff")
    list_filter = ("user__is_staff", ("created", admin.DateFieldListFilter))
    search_fields = ("user__email", "user__first_name", "user__last_name")
    date_hierarchy = "created"

    @admin.display(boolean=True, description="Staff", ordering="user__is_staff")
    def is_staff(self, obj):
        return obj.user.is_staff

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False


class ActiveDayAdmin(LoginEventAdmin):
    """Read-only log of the days each user used the site, written by ActiveUserMiddleware."""
    list_display = ("date", "user", "is_staff")
    list_filter = ("user__is_staff", "date")
    date_hierarchy = "date"


class DashboardOpenAdmin(LoginEventAdmin):
    """Read-only count of Live Dashboard opens per person per day, written by finances.views.live_dashboard."""
    list_display = ("date", "user", "count")
    list_filter = ("date",)
    date_hierarchy = "date"


class DataRetentionEventAdmin(TCSPModelAdmin):
    """Read-only audit log written by users.retention. Holds ids, never personal details."""
    list_display = ("created", "user_id", "action", "performed_by_id", "detail")
    list_filter = ("action", ("created", admin.DateFieldListFilter))
    search_fields = ("=user_id",)
    date_hierarchy = "created"

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
users_admin_site.register(LoginEvent, LoginEventAdmin)
users_admin_site.register(ActiveDay, ActiveDayAdmin)
users_admin_site.register(DashboardOpen, DashboardOpenAdmin)
users_admin_site.register(DataRetentionEvent, DataRetentionEventAdmin)
users_admin_site.register(Product, ProductAutocompleteAdmin)
users_admin_site.register(Term, TermAutocompleteAdmin)
