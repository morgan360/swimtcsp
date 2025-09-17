# custom_admins/lessonsadmin.py
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin import AdminSite
from django.urls import path
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from lessons_bookings.models import LessonEnrollment
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from django.http import FileResponse
import io
from django.shortcuts import redirect
from utils.terms_utils import get_current_term

# ✅ Custom Admin Site
class LessonsAdminSite(AdminSite):
    site_header = "🏫 Lessons Admin"
    site_title = "Lessons Admin Portal"
    index_title = "Manage Lesson Programs and Terms"

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context


# ✅ Exported instance
lessons_admin_site = LessonsAdminSite(name="lessonsadmin")


# ✅ Admin for LessonEnrollment
class LessonEnrollmentAdmin(admin.ModelAdmin):
    list_display = ["swimling", "simple_term", "lesson", "order_link"]
    list_display_links = ("swimling",)
    raw_id_fields = ["swimling"]
    list_filter = [
        ("term", RelatedDropdownFilter),
        ("lesson", RelatedDropdownFilter),
        ("lesson__category", RelatedDropdownFilter),
    ]
    search_fields = [
        "swimling__first_name",
        "swimling__last_name",
        "swimling__guardian__last_name",
        "swimling__guardian__email",
        "lesson__name",
        "lesson__category__name",
        "term__name",
        "order__id",
    ]
    list_per_page = 20

    def simple_term(self, obj):
        return f"Term {obj.term.id}" if obj.term else "-"

    simple_term.short_description = "Term"
    # ✅ Pretty link to related order
    def order_link(self, obj):
        if hasattr(obj, "order") and obj.order:
            return format_html(
                '<a href="/lessonsadmin/lessons_orders/order/{}/change/">Order #{}</a>',
                obj.order.id,
                obj.order.id,
            )
        return "-"

    order_link.short_description = "Order"

    # ✅ Override changelist to default to current term
    def changelist_view(self, request, extra_context=None):
        if not request.GET:  # only if no filters applied
            current_term = get_current_term()
            if current_term:
                query = request.GET.copy()
                query["term__id__exact"] = str(current_term.id)  # ✅ correct key
                from django.shortcuts import redirect
                return redirect(f"{request.path}?{query.urlencode()}")
        return super().changelist_view(request, extra_context=extra_context)

    def response_redirect(self, request, url):
        """Small helper to make redirects cleaner"""
        from django.shortcuts import redirect
        return redirect(url)

    # ✅ Add custom print view
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path("print/", self.admin_site.admin_view(self.print_view), name="lesson_enrollment_print"),
        ]
        return custom_urls + urls

    def print_view(self, request):
        queryset = self.get_queryset(request)

        # ✅ Apply filters safely
        clean_filters = {k.lstrip("?"): v for k, v in request.GET.items() if v}
        if clean_filters:
            try:
                queryset = queryset.filter(**clean_filters)
            except Exception:
                pass  # ignore bad filters

        buffer = io.BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=A4)

        data = [["ID", "Swimling", "Term", "Lesson", "Changed By"]]
        for obj in queryset:
            data.append([
                str(obj.id),
                str(obj.swimling) if obj.swimling else "",
                obj.term.label if obj.term else "",
                str(obj.lesson) if obj.lesson else "",
                str(obj.changed_by) if obj.changed_by else "-",
            ])

        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
            ("GRID", (0, 0), (-1, -1), 0.5, colors.black),
            ("ALIGN", (0, 0), (-1, -1), "LEFT"),
        ]))

        doc.build([table])
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename="enrollments.pdf")

    class Media:
        js = ("js/add_print_button.js",)  # 👈 still adds Print button in admin toolbar

# ✅ Register the model to the custom admin site
lessons_admin_site.register(LessonEnrollment, LessonEnrollmentAdmin)
