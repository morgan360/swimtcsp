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






User = get_user_model()


# 🔹 Admin site
class UsersAdminSite(AdminSite):
    site_header = '👤 Users Admin'
    site_title = 'Users Admin Portal'
    index_title = 'Manage Users, Swimlings, and Permissions'

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context


users_admin_site = UsersAdminSite(name='usersadmin')


# 🔹 Inlines
class SwimlingInline(admin.StackedInline):
    model = Swimling
    extra = 1
    fields = ('first_name', 'last_name', 'dob', 'sco_role_num', 'notes')


# 🔹 Swimling Admin
class SwimlingAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SwimlingResource
    list_display = ['first_name', 'last_name', 'guardian_link']
    list_filter = [
        ('last_name', DropdownFilter),
        ('first_name', DropdownFilter),
        ('guardian', RelatedDropdownFilter),
    ]
    ordering = ['guardian__last_name', 'last_name']

    def guardian_link(self, obj):
        if obj.guardian:
            try:
                url = reverse(
                    "usersadmin:%s_%s_change" % (
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
class GroupAdmin(BaseGroupAdmin, ImportExportModelAdmin):
    resource_class = GroupResource


# 🔹 Register with default admin (for Hijack compatibility)
try:
    admin.site.register(User, UserAdmin)
except admin.sites.AlreadyRegistered:
    pass

# 🔹 Register all
users_admin_site.register(User, UserAdmin)
users_admin_site.register(Swimling, SwimlingAdmin)
users_admin_site.register(Group, GroupAdmin)
