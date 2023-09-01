from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Swimling
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils.html import format_html
from .models import User, UserProfile, Swimling
from django.contrib.auth import get_user_model
from .resources import SwimlingResource, UserResource
from import_export.admin import ImportExportMixin


@admin.register(Swimling)
class SwimlingAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = SwimlingResource
    list_display = ['first_name', 'last_name', 'guardian_link']  # Replace 'guardian' with 'guardian_link'
    list_filter = ('last_name', 'first_name', 'guardian',)

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
class UserAdmin(ImportExportMixin, BaseUserAdmin):
    resource_class = UserResource
    inlines = [SwimlingInline]
    fieldsets = (
        (None, {'fields': (
            'email', 'password', 'mobile_phone', 'first_name', 'last_name','notes',  'last_login')}),
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

    display_groups.short_description = 'Groups'  # Set the column hea

    list_display = ('email', 'first_name','last_name', 'mobile_phone', 'notes', 'display_groups', 'last_login')
    list_filter = ('last_name', 'groups',)
    search_fields = ('email', 'last_name','first_name',)
    ordering = ('last_name','first_name',)
    filter_horizontal = ('groups', 'user_permissions',)
