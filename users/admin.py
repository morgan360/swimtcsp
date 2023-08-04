from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from .models import User, UserProfile, Swimling


class SwimlingInline(admin.StackedInline):
    model = Swimling
    extra = 1  # Set the number of empty forms to display for adding new Swimlings
    fields = ('first_name', 'last_name', 'dob', 'school_role_number', 'notes',)

class UserProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False


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


admin.site.register(User, UserAdmin)
