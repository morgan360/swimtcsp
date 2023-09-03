# Responsible for defining what goes into the Lesson Admin area
from django.contrib.admin import AdminSite
from lessons.models import Program, Area, Category, Product
from users.models import User, Swimling
from django.contrib.admin import AdminSite
from django.contrib.auth.models import Group

class UsersAdminSite(AdminSite):
    site_header = 'Users Admin'
    site_title = 'Users Admin'


users_admin_site = UsersAdminSite(name='usersadmin')
# Register your model(s)
models = [Group]
for model in models:
    users_admin_site.register(model)
