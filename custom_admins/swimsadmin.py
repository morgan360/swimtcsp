from django.contrib.admin import AdminSite
from swims.models import PublicSwimCategory, PublicSwimProduct, PriceVariant
from users.models import User
from django.contrib.auth.models import Group

from custom_admins.panels import operations_site




# Panel consolidation: this name now points at the shared panel.
swims_admin_site = operations_site
# Register models explicitly
# swims_admin_site.register(PublicSwimCategory)
# swims_admin_site.register(PublicSwimProduct)
# swims_admin_site.register(PriceVariant)
# swims_admin_site.register(Group)  # Optional: if needed
