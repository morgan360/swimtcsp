from django.contrib.admin import AdminSite, ModelAdmin
from django.contrib.auth.models import Group
from django.utils.html import format_html
from django.urls import reverse
from users.models import User, Swimling


class UsersAdminSite(AdminSite):
    site_header = '👤 Users Admin'
    site_title = 'Users Admin Portal'
    index_title = 'Manage Users, Swimlings, and Permissions'

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context


users_admin_site = UsersAdminSite(name='usersadmin')


# ✅ Custom admin for User (optional fields/display)
class UserAdmin(ModelAdmin):
    list_display = ("email", "first_name", "last_name", "is_active", "is_staff")


# ✅ Safe Swimling admin with guardian link
class SwimlingAdmin(ModelAdmin):
    list_display = ("first_name", "last_name", "guardian_link")

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
            except Exception as e:
                # Optional: log e here
                return f"{obj.guardian.first_name} {obj.guardian.last_name or ''}".strip()
        return "-"


# Register models with usersadmin
users_admin_site.register(User, UserAdmin)
users_admin_site.register(Swimling, SwimlingAdmin)
users_admin_site.register(Group)
