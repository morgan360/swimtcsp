# Responsible for defining what goes into the Lesson Admin area
from django.contrib.admin import AdminSite
from lessons.models import Program,  Category, Product
from users.models import User, Swimling
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group

class SwimsAdminSite(AdminSite):
    site_header = 'Swims Admin'
    site_title = 'Swims Admin'


swims_admin_site = SwimsAdminSite(name='swimsadmin')
# Register your model(s)
models = []
for model in models:
    swims_admin_site.register(model)
