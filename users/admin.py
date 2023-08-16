from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Swimling
from django.contrib.sessions.models import Session
from django.urls import reverse
from django.utils.html import format_html
from .models import User, UserProfile, Swimling
from django.contrib.auth import get_user_model

class SwimlingInline(admin.StackedInline):
    model = Swimling
    extra = 1  # Set the number of empty forms to display for adding new Swimlings
    fields = ('first_name', 'last_name', 'dob', 'school_role_number', 'notes',)


class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False

User = get_user_model()

@admin.register(User)
class UserAdmin(BaseUserAdmin):
    inlines = [SwimlingInline]
    fieldsets = (
        (None, {'fields': (
            'email', 'password', 'first_name', 'last_name', 'last_login')}),
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

    list_display = ('email', 'first_name', 'is_staff', 'last_login')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email',)
    ordering = ('email',)
    filter_horizontal = ('groups', 'user_permissions',)


# admin.site.register(User, UserAdmin)


# View Session Data

class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()

    list_display = ['session_key', '_session_data', 'expire_date']
    # list_display = ()
    actions = ['view_selected_session']

    def view_selected_session(self, request, queryset):
        for session in queryset:
            session_data = session.get_decoded()
            # Your custom action logic here
            # For demonstration, just printing session data
            print(session_data)

    view_selected_session.short_description = "View selected session data"

    def view_session(self, obj):
        url = reverse('admin:view_session', args=[obj.session_key])
        return format_html('<a href="{}">View</a>', url)

    view_session.short_description = 'View'


admin.site.register(Session, SessionAdmin)
