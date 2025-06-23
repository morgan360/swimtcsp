from django.contrib.admin import AdminSite

class LessonsAdminSite(AdminSite):
    site_header = "🏫 Lessons Admin"
    site_title = "Lessons Admin Portal"
    index_title = "Manage Lesson Programs and Terms"

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context

# ✅ THIS must be present:
lessons_admin_site = LessonsAdminSite(name='lessonsadmin')