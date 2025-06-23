from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin, GroupAdmin as BaseGroupAdmin
from import_export.admin import ImportExportMixin, ImportExportModelAdmin
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter
from django.urls import reverse
from django.utils.html import format_html
from hijack.contrib.admin import HijackUserAdminMixin

from .models import UserProfile, Swimling
from .resources import SwimlingResource, UserResource, GroupResource
from custom_admins.usersadmin import users_admin_site

# Inline admin for Swimlings on User
def guardian_label(obj):
    return f"{obj.guardian.first_name} {obj.guardian.last_name}" if obj.guardian else "No Guardian"
guardian_label.short_description = 'Guardian'

def guardian_ordering(obj):
    return obj.guardian.last_name if obj.guardian else ""

class SwimlingInline(admin.StackedInline):
    model = Swimling
    extra = 1
    fields = ('first_name', 'last_name', 'dob', 'sco_role_num', 'notes')

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False

# Swimling admin
class SwimlingAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SwimlingResource
    list_display = ['first_name', 'last_name', 'guardian_display']
    list_filter = [
        ('last_name', DropdownFilter),
        ('first_name', DropdownFilter),
        ('guardian', RelatedDropdownFilter),
    ]
    ordering = ['guardian__last_name', 'last_name']

    def guardian_display(self, obj):
        if obj.guardian:
            try:
                url = reverse(
                    "usersadmin:%s_%s_change" % (
                        obj.guardian._meta.app_label,
                        obj.guardian._meta.model_name
                    ),
                    args=[obj.guardian.pk]
                )
                return format_html('<a href="{}">{}</a>', url, f"{obj.guardian.first_name} {obj.guardian.last_name}")
            except:
                return f"{obj.guardian.first_name} {obj.guardian.last_name}"
        return "-"
    guardian_display.short_description = 'Guardian'


class SwimlingAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SwimlingResource
    list_display = ['first_name', 'last_name', 'guardian_link']  # ✅ Use correct method name

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
                name = f"{obj.guardian.first_name} {obj.guardian.last_name or ''}".strip()
                return format_html('<a href="{}">{}</a>', url, name)
            except Exception:
                return f"{obj.guardian.first_name} {obj.guardian.last_name or ''}".strip()
        return "-"
    guardian_link.short_description = 'Guardian'

# User admin
User = get_user_model()
class UserAdmin(HijackUserAdminMixin, ImportExportMixin, BaseUserAdmin):
    resource_class = UserResource
    list_per_page = 20
    inlines = [UserProfileInline, SwimlingInline]

    fieldsets = (
        (None, {'fields': ('email', 'password', 'mobile_phone', 'first_name', 'last_name', 'admin_notes', 'last_login')}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
        ('Groups and Permissions', {'fields': ('groups', 'user_permissions')})
    )

    readonly_fields = ('user_permissions',)  # Make permissions readonly

    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'password1', 'password2')
        }),
    )

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'

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

# Group admin
class GroupAdmin(BaseGroupAdmin, ImportExportModelAdmin):
    resource_class = GroupResource

# Safe registration with users_admin_site only
from django.contrib.admin.sites import AlreadyRegistered, NotRegistered

try:
    users_admin_site.unregister(User)
except NotRegistered:
    pass

try:
    users_admin_site.unregister(Swimling)
except NotRegistered:
    pass

try:
    users_admin_site.unregister(Group)
except NotRegistered:
    pass

users_admin_site.register(User, UserAdmin)
users_admin_site.register(Swimling, SwimlingAdmin)
users_admin_site.register(Group, GroupAdmin)

# Optional: unregister from default site if not needed
try:
    admin.site.unregister(Group)
except NotRegistered:
    pass
