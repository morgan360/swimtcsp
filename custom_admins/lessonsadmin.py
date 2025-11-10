# custom_admins/lessonsadmin.py
from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin import AdminSite
from django.urls import path
from django_admin_listfilter_dropdown.filters import RelatedDropdownFilter

from lessons_bookings.models import LessonEnrollment, Term
from users.models import Swimling
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle
from reportlab.lib import colors
from django.http import FileResponse, HttpResponse
import io
import csv
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
    autocomplete_fields = ["swimling"]
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
        "term__id",  # ✅ search directly by Term ID
        "order__id",
    ]

    list_per_page = 20

    def simple_term(self, obj):
        return f"Term {obj.term.id}" if obj.term else "-"

    simple_term.short_description = "Term"
    simple_term.admin_order_field = "term__id"
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

    # ✅ Admin action to export swimmers in current term but not in next term
    def export_not_rebooked(self, request, queryset):
        """Export swimmers enrolled in current term but not in next term as CSV"""
        current_term = Term.get_current_term()
        next_term = Term.get_next_term()

        if not current_term:
            self.message_user(request, "No current term found.", level='error')
            return

        if not next_term:
            self.message_user(request, "No next term found.", level='error')
            return

        # Get all swimlings enrolled in current term
        current_enrollments = LessonEnrollment.objects.filter(
            term=current_term
        ).select_related('swimling', 'swimling__guardian', 'lesson', 'lesson__category')

        # Get all swimlings enrolled in next term
        next_term_swimlings = set(
            LessonEnrollment.objects.filter(term=next_term).values_list('swimling_id', flat=True)
        )

        # Filter to only those NOT in next term
        not_rebooked = current_enrollments.exclude(swimling_id__in=next_term_swimlings)

        # Create CSV response
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="not_rebooked_term_{current_term.id}_to_{next_term.id}.csv"'

        writer = csv.writer(response)
        writer.writerow([
            'Guardian Email',
            'Guardian First Name',
            'Guardian Last Name',
            'Guardian Mobile',
            'Swimling First Name',
            'Swimling Last Name',
            'Swimling DOB',
            'Current Lesson',
            'Lesson Category',
            'Current Term'
        ])

        for enrollment in not_rebooked:
            guardian = enrollment.swimling.guardian
            writer.writerow([
                guardian.email if guardian else '',
                guardian.first_name if guardian else '',
                guardian.last_name if guardian else '',
                str(guardian.mobile_phone) if guardian and guardian.mobile_phone else '',
                enrollment.swimling.first_name,
                enrollment.swimling.last_name,
                enrollment.swimling.dob.strftime('%Y-%m-%d') if enrollment.swimling.dob else '',
                enrollment.lesson.name if enrollment.lesson else '',
                enrollment.lesson.category.name if enrollment.lesson and enrollment.lesson.category else '',
                f"Term {enrollment.term.id}"
            ])

        self.message_user(
            request,
            f"Exported {not_rebooked.count()} enrollments from Term {current_term.id} not rebooked in Term {next_term.id}."
        )
        return response

    export_not_rebooked.short_description = "Export swimmers not rebooked in next term (CSV)"

    # Register the action
    actions = ['export_not_rebooked']

    class Media:
        js = ("js/add_print_button.js",)  # 👈 still adds Print button in admin toolbar

# ✅ Lightweight admin to power Swimling autocomplete while hiding it from the menu
class SwimlingAutocompleteAdmin(admin.ModelAdmin):
    search_fields = [
        "first_name",
        "last_name",
        "guardian__first_name",
        "guardian__last_name",
        "guardian__email",
    ]

    def has_module_permission(self, request):  # hide from the left nav
        return False


# ✅ Register the model to the custom admin site
lessons_admin_site.register(Swimling, SwimlingAutocompleteAdmin)
lessons_admin_site.register(LessonEnrollment, LessonEnrollmentAdmin)
