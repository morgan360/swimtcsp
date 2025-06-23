from django.contrib.admin import AdminSite
from schools.models import ScoLessons, ScoCategory, ScoProgram, ScoSchool
from schools_orders.models import Order
from schools_bookings.models import ScoTerm, ScoEnrollment


class SchoolsAdminSite(AdminSite):
    site_header = "🏫 Schools Admin"
    site_title = "Schools Admin Portal"
    index_title = "Manage School Programs and Bookings"

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context


schools_admin_site = SchoolsAdminSite(name='schoolsadmin')