import os
from django.contrib.admin import AdminSite, TabularInline, ModelAdmin
from navigation.models import MenuGroup, MenuItem
from waiting_list.models import WaitingList  # ✅ Import your model
from django.contrib import admin, messages
from django.utils.html import format_html
from import_export import resources, fields
from import_export.admin import ExportActionMixin
from progress.models import (
    CoreAquaticSkill,
    Skill,
    CategorySkill,
    SkillAssessment,
    InstructorNote
)
from chatbot.models import ChatbotQuery, FAQEntry
import openai
from openai import OpenAI
from lessons_bookings.models import LessonEnrollment, Term
from django.contrib.admin import SimpleListFilter
from django.conf import settings
import time
import logging

### START ###
logger = logging.getLogger(__name__)

class GeneralAdminSite(AdminSite):
    site_header = "⚙️ General Admin"
    site_title = "General Admin Portal"
    index_title = "Manage Navigation, Timetables, and Settings"

    def each_context(self, request):
        context = super().each_context(request)
        context["custom_css"] = "css/shared_admin.css"
        return context

general_admin_site = GeneralAdminSite(name='generaladmin')

# ✅ Inline: show MenuItems under MenuGroup
class MenuItemInline(admin.StackedInline):
    model = MenuItem
    extra = 1
    can_delete = True
    show_change_link = True
    classes = ['collapse']

# ✅ Custom MenuGroup admin with inlines
class MenuGroupAdmin(ModelAdmin):
    list_display = ['name']
    inlines = [MenuItemInline]

class MenuItemAdmin(ModelAdmin):
    list_display = ('label', 'is_active', 'group', 'url_name', 'requires_login', 'requires_staff')
    list_display_links = ('label',)
    list_editable = ('is_active',)
    list_filter = ('group', 'is_active', 'requires_login', 'requires_staff')
    search_fields = ('label', 'url_name', 'external_url')

# ✅ WAITIG LIST
class HasSiblingEnrolledFilter(SimpleListFilter):
    title = 'Sibling Enrolled'
    parameter_name = 'sibling_enrolled'

    def lookups(self, request, model_admin):
        return (
            ('yes', 'Yes'),
            ('no', 'No'),
        )

    def queryset(self, request, queryset):
        current_term_id = Term.get_current_term_id()
        if not current_term_id:
            return queryset

        swimling_ids_with_sibling = set()
        for obj in queryset.select_related('swimling'):
            guardian = obj.swimling.guardian
            has_sibling = LessonEnrollment.objects.filter(
                swimling__guardian=guardian,
                term_id=current_term_id
            ).exclude(swimling=obj.swimling).exists()
            if has_sibling:
                swimling_ids_with_sibling.add(obj.id)

        if self.value() == 'yes':
            return queryset.filter(id__in=swimling_ids_with_sibling)
        elif self.value() == 'no':
            return queryset.exclude(id__in=swimling_ids_with_sibling)

        return queryset

class WaitingListResource(resources.ModelResource):
    swimling_first_name = fields.Field(column_name='First Name')
    swimling_last_name = fields.Field(column_name='Last Name')
    swimling_dob = fields.Field(column_name='DoB')
    product_name = fields.Field(column_name='Product')
    guardian_name = fields.Field(column_name='Guardian')
    guardian_email = fields.Field(column_name='Email')
    guardian_phone = fields.Field(column_name='Phone')
    notes = fields.Field(attribute='notes', column_name='Notes')
    is_transfer_request = fields.Field(attribute='is_transfer_request', column_name='Transfer Request')
    is_notified = fields.Field(attribute='is_notified', column_name='Notified')
    assigned_lesson_name = fields.Field(column_name='Assigned Lesson')
    completed = fields.Field(attribute='completed', column_name='Completed')
    created_at = fields.Field(column_name='Created')

    class Meta:
        model = WaitingList
        fields = (
            'swimling_first_name', 'swimling_last_name', 'swimling_dob', 'product_name',
            'guardian_name', 'guardian_email', 'guardian_phone',
            'is_transfer_request', 'notes', 'is_notified',
            'assigned_lesson_name', 'completed', 'created_at',
        )
        export_order = fields

    def dehydrate_swimling_first_name(self, obj):
        return obj.swimling.first_name

    def dehydrate_swimling_last_name(self, obj):
        return obj.swimling.last_name

    def dehydrate_swimling_dob(self, obj):
        dob = obj.swimling.dob
        return dob.strftime('%d %b %Y') if dob else ''

    def dehydrate_product_name(self, obj):
        return str(obj.product)

    def dehydrate_guardian_name(self, obj):
        return str(obj.swimling.guardian)

    def dehydrate_guardian_email(self, obj):
        return obj.swimling.guardian.email

    def dehydrate_guardian_phone(self, obj):
        phone = obj.swimling.guardian.mobile_phone
        return str(phone) if phone else ''

    def dehydrate_assigned_lesson_name(self, obj):
        return str(obj.assigned_lesson) if obj.assigned_lesson else ''

    def dehydrate_created_at(self, obj):
        return obj.created_at.strftime('%d %b %Y')

class WaitingListAdmin(ExportActionMixin, admin.ModelAdmin):
    resource_classes = [WaitingListResource]
    change_list_template = 'admin/waiting_list/waitinglist/change_list.html'

    list_display = (
        'swimling', 'get_dob', 'get_product', 'get_guardian', 'get_guardian_email', 'get_guardian_phone',
        'is_transfer_request', 'get_notes',
        'has_enrolled_sibling', 'is_notified', 'assigned_lesson', 'completed', 'get_created_at'
    )
    list_filter = ('is_notified', 'is_transfer_request', 'created_at', HasSiblingEnrolledFilter)

    search_fields = (
        'swimling__first_name', 'swimling__last_name', 'product__name', 'swimling__guardian__email'
    )

    def get_dob(self, obj):
        dob = obj.swimling.dob
        return dob.strftime('%d %b %Y') if dob else '-'
    get_dob.short_description = "DoB"
    get_dob.admin_order_field = 'swimling__dob'

    def get_guardian(self, obj):
        return obj.swimling.guardian
    get_guardian.short_description = "Guardian"
    get_guardian.admin_order_field = 'swimling__guardian'

    def get_guardian_email(self, obj):
        return obj.swimling.guardian.email
    get_guardian_email.short_description = "Email"
    get_guardian_email.admin_order_field = 'swimling__guardian__email'

    def get_guardian_phone(self, obj):
        phone = obj.swimling.guardian.mobile_phone
        return phone if phone else '-'
    get_guardian_phone.short_description = "Phone"

    def get_product(self, obj):
        name = str(obj.product)
        if len(name) > 50:
            return format_html('<span title="{}">{}&hellip;</span>', name, name[:50])
        return name
    get_product.short_description = "Product"
    get_product.admin_order_field = 'product'

    def get_notes(self, obj):
        if not obj.notes:
            return '-'
        if len(obj.notes) > 50:
            return format_html('<span title="{}">{}&hellip;</span>', obj.notes, obj.notes[:50])
        return obj.notes
    get_notes.short_description = "Notes"

    def get_created_at(self, obj):
        return obj.created_at.strftime('%d %b %Y')
    get_created_at.short_description = "Created"
    get_created_at.admin_order_field = 'created_at'

    def has_enrolled_sibling(self, obj):
        current_term_id = Term.get_current_term_id()
        if not current_term_id:
            return False

        return LessonEnrollment.objects.filter(
            swimling__guardian=obj.swimling.guardian,
            term_id=current_term_id
        ).exclude(
            swimling=obj.swimling
        ).exists()
    has_enrolled_sibling.short_description = "Sibling Enrolled"
    has_enrolled_sibling.boolean = True

try:
    general_admin_site.unregister(MenuItem)
except admin.sites.NotRegistered:
    pass


###### Skills ########

# Optional: Customize how each appears
class CoreAquaticSkillAdmin(ModelAdmin):
    list_display = ['abbreviation', 'name']
    search_fields = ['abbreviation', 'name']

class SkillAdmin(ModelAdmin):
    list_display = ['code', 'name', 'cas']
    search_fields = ['code', 'name']
    list_filter = ['cas']

class CategorySkillAdmin(ModelAdmin):
    list_display = ['category', 'skill', 'order', 'get_stage']
    search_fields = ['category__name', 'skill__name']
    list_filter = ['category__stage', 'category']

    def get_stage(self, obj):
        return obj.category.stage
    get_stage.short_description = "Stage"

    def get_ordering(self, request):
        # First by category.stage, then by CategorySkill.order
        return ['category__stage', 'order']

class SkillAssessmentAdmin(ModelAdmin):
    list_display = ['swimling', 'skill', 'term', 'rating', 'instructor']
    list_filter = ['term', 'rating', 'instructor']
    search_fields = ['swimling__first_name', 'swimling__last_name', 'skill__name']

class InstructorNoteAdmin(ModelAdmin):
    list_display = ['swimling', 'term', 'instructor', 'created_at']
    search_fields = ['swimling__first_name', 'swimling__last_name', 'note']
    list_filter = ['term', 'instructor']

######## AI Splash BOT ############
EMBED_MODEL = os.getenv(
    "OPENAI_EMBED_MODEL",
    getattr(settings, "OPENAI_EMBED_MODEL", "text-embedding-3-small"),
)

class ChatbotQueryAdmin(admin.ModelAdmin):
    list_display = ("source", "timestamp", "short_message", "short_response", "response_type", "confidence_score")
    readonly_fields = ("user", "session_key", "source", "message", "response", "response_type", "confidence_score", "timestamp")

    def short_message(self, obj):
        if not obj.message:
            return "-"
        return (obj.message[:50] + "...") if len(obj.message) > 50 else obj.message

    short_message.short_description = "Message"

    def short_response(self, obj):
        if not obj.response:
            return "-"
        return (obj.response[:50] + "...") if len(obj.response) > 50 else obj.response

    short_response.short_description = "Response"

# Frequently Asked Questions

client = OpenAI()

@admin.action(description="Generate embeddings using OpenAI")
def generate_embeddings(modeladmin, request, queryset):
    """
    Re-embed selected FAQs using the model from OPENAI_EMBED_MODEL.
    """
    count = 0
    errors = 0

    for faq in queryset.iterator():
        if not faq.question:
            continue
        try:
            resp = client.embeddings.create(
                model=EMBED_MODEL,
                input=faq.question.strip(),
            )
            faq.embedding = resp.data[0].embedding
            faq.save(update_fields=["embedding", "updated"])
            count += 1

        except Exception as e:
            errors += 1
            logger.exception("Embedding failed for FAQ id=%s question=%r", faq.id, faq.question[:80])
            messages.warning(request, f"❌ Error for '{faq.question[:60]}': {e}")
            # optional tiny backoff for transient rate limits
            time.sleep(0.25)

    if count:
        messages.success(request, f"✅ Generated embeddings for {count} FAQ(s) using {EMBED_MODEL}.")
    if errors and not count:
        messages.error(request, f"⚠️ No embeddings created. Last error: {e}")
    elif errors:
        messages.warning(request, f"⚠️ {errors} item(s) failed; see logs for details.")


@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = ("question", "short_answer", "lessons_only", "updated")
    list_filter = ("lessons_only",)
    search_fields = ("question", "answer")
    actions = [generate_embeddings]

    def short_answer(self, obj):
        return (obj.answer[:80] + "...") if obj.answer and len(obj.answer) > 80 else obj.answer
    short_answer.short_description = "Answer"


# ✅ Register all skills-related models
general_admin_site.register(CoreAquaticSkill, CoreAquaticSkillAdmin)
general_admin_site.register(Skill, SkillAdmin)
general_admin_site.register(CategorySkill, CategorySkillAdmin)
general_admin_site.register(SkillAssessment, SkillAssessmentAdmin)
general_admin_site.register(InstructorNote, InstructorNoteAdmin)

# ✅ Register models to general admin site
general_admin_site.register(MenuGroup, MenuGroupAdmin)
general_admin_site.register(WaitingList, WaitingListAdmin)  # ✅ Registered here
general_admin_site.register(MenuItem, MenuItemAdmin)
general_admin_site.register(ChatbotQuery, ChatbotQueryAdmin)
general_admin_site.register(FAQEntry, FAQEntryAdmin)