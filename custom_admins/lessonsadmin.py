# Responsible for defining what goes into the Lesson Admin area
from django.contrib.admin import AdminSite
from lessons.models import Program, Area, Category, Product
from lessons_bookings.models import Term
from django.contrib.admin import AdminSite


class LessonsAdminSite(AdminSite):
    site_header = 'Lessons Admin'
    site_title = 'Lessons Admin'


lessons_admin_site = LessonsAdminSite(name='lessonsadmin')
# Register your model(s)
models = []
for model in models:
    lessons_admin_site.register(model)
