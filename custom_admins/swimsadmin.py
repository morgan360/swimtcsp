from django.contrib.admin import AdminSite
from swims.models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from users.models import User
from django.contrib.auth.models import Group


class SwimsAdminSite(AdminSite):
    site_header = '🏊 Swims Admin'
    site_title = 'Swims Admin Portal'
    index_title = 'Manage Public Swims, Prices, and Access'

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"  # Shared style across admin panels
        return context


swims_admin_site = SwimsAdminSite(name='swimsadmin')

# Register models explicitly
# swims_admin_site.register(PublicSwimCategory)
# swims_admin_site.register(PublicSwimProduct)
# swims_admin_site.register(PriceVariant)
# swims_admin_site.register(Group)  # Optional: if needed
