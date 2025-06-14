from django.contrib import admin
from django.contrib.auth.models import Group
from django.contrib.auth.admin import GroupAdmin as BaseGroupAdmin
from .models import User, UserProfile, Swimling
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils.html import format_html
from .models import User, UserProfile, Swimling
from django.contrib.auth import get_user_model
from .resources import SwimlingResource, UserResource, GroupResource
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from import_export.admin import ImportExportMixin
from import_export import resources
from import_export.admin import ImportExportModelAdmin
from custom_admins.usersadmin import users_admin_site
from django_admin_listfilter_dropdown.filters import DropdownFilter, RelatedDropdownFilter, ChoiceDropdownFilter
from hijack.contrib.admin import HijackUserAdminMixin

@admin.register(Swimling)
class SwimlingAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SwimlingResource
    list_display = ['first_name', 'last_name', 'guardian_link']  # Replace 'guardian' with 'guardian_link'
    list_filter = [('last_name', DropdownFilter), ('first_name', DropdownFilter),('guardian',RelatedDropdownFilter)]

    def guardian_link(self, obj):
        if obj.guardian:
            url = reverse("admin:%s_%s_change" % (obj.guardian._meta.app_label, obj.guardian._meta.model_name),
                          args=[obj.guardian.pk])
            return format_html('<a href="{}">{}</a>', url, obj.guardian)
        return None

    guardian_link.short_description = 'Guardian'
#


class SwimlingInline(admin.StackedInline):
    model = Swimling
    extra = 1  # Set the number of empty forms to display for adding new Swimlings
    fields = ('first_name', 'last_name', 'dob', 'sco_role_num', 'notes',)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


User = get_user_model()


@admin.register(User)
class UserAdmin(HijackUserAdminMixin, ImportExportMixin, BaseUserAdmin):
    resource_class = UserResource
    list_per_page = 20
    inlines = [SwimlingInline]
    fieldsets = (
        (None, {'fields': (
            'email', 'password', 'mobile_phone', 'first_name', 'last_name','admin_notes',  'last_login')}),
        ('Permissions', {'fields': (
            'is_active', 'is_staff', 'is_superuser', 'groups',
            'user_permissions')}),
    )
    add_fieldsets = (
        (
            None,
            {
                'classes': ('wide',),
                'fields': ('email', 'password1', 'password2')
            }
        ),
    )

    def display_groups(self, obj):
        return ', '.join([group.name for group in obj.groups.all()])

    display_groups.short_description = 'Groups'
    list_display = ('get_user_id', 'email', 'full_name', 'username', 'mobile_phone', 'display_groups',)
    # Define the get_user_id method
    def get_user_id(self, obj):
        return obj.id
    get_user_id.short_description = 'User ID'  # Set the column header

    list_display = ('get_user_id', 'email',  'username', 'mobile_phone', 'display_groups',)
    list_filter = [('last_name', DropdownFilter), ('first_name', DropdownFilter), ('groups', RelatedDropdownFilter)]
    search_fields = ('email', 'last_name', 'first_name',)
    ordering = ('last_name', 'first_name',)
    filter_horizontal = ('groups', 'user_permissions',)

    def full_name(self, obj):
        return f"{obj.first_name} {obj.last_name}"
    full_name.short_description = 'Full Name'

users_admin_site.register(User, UserAdmin)
users_admin_site.register(Swimling, SwimlingAdmin)


# class GroupResource(resources.ModelResource):
#     class Meta:
#         model = Group


class GroupAdmin(BaseGroupAdmin, ImportExportModelAdmin):
    resource_class = GroupResource

# Unregister the original Group admin and register with the custom one
admin.site.unregister(Group)
users_admin_site.unregister(Group)
admin.site.register(Group, GroupAdmin)
users_admin_site.register(Group,GroupAdmin)
