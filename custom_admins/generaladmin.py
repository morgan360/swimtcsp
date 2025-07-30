import os
from django.contrib.admin import AdminSite, TabularInline, ModelAdmin
from navigation.models import MenuGroup, MenuItem
from waiting_list.models import WaitingList  # ✅ Import your model
from django.contrib import admin, messages
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

# ✅ Optional: customize WaitingList admin
class WaitingListAdmin(ModelAdmin):
    list_display = ['swimling', 'product', 'is_notified', 'notification_date', "completed"]
    list_filter = ['is_notified', 'completed']
    search_fields = ['swimling__name', 'user__email', 'product__name']

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
    list_display = ['category', 'skill', 'order']
    search_fields = ['category__name', 'skill__name']
    list_filter = ['category']

class SkillAssessmentAdmin(ModelAdmin):
    list_display = ['swimling', 'skill', 'term', 'level', 'instructor']
    list_filter = ['term', 'level', 'instructor']
    search_fields = ['swimling__first_name', 'swimling__last_name', 'skill__name']

class InstructorNoteAdmin(ModelAdmin):
    list_display = ['swimling', 'term', 'instructor', 'created_at']
    search_fields = ['swimling__first_name', 'swimling__last_name', 'note']
    list_filter = ['term', 'instructor']


class ChatbotQueryAdmin(admin.ModelAdmin):
    list_display = ("source", "timestamp", "short_message", "response_type", "confidence_score")

    def short_message(self, obj):
        if not obj.message:
            return "-"
        return (obj.message[:50] + "...") if len(obj.message) > 50 else obj.message

    short_message.short_description = "Message"

# Frequently Asked Questions

client = OpenAI()  # Uses OPENAI_API_KEY from env automatically

@admin.action(description="Generate embeddings using OpenAI (new client)")
def generate_embeddings(modeladmin, request, queryset):
    count = 0
    for faq in queryset:
        if not faq.question:
            continue
        try:
            response = client.embeddings.create(
                input=faq.question,
                model="text-embedding-ada-002"
            )
            faq.embedding = response.data[0].embedding
            faq.save()
            count += 1
        except Exception as e:
            messages.warning(request, f"❌ Error for '{faq.question[:50]}': {e}")
    messages.success(request, f"✅ Generated embeddings for {count} FAQs.")

@admin.register(FAQEntry)
class FAQEntryAdmin(admin.ModelAdmin):
    list_display = ('question', 'short_answer', 'lessons_only', 'updated')
    list_filter = ('lessons_only',)
    search_fields = ('question', 'answer')
    actions = [generate_embeddings]

    def short_answer(self, obj):
        return (obj.answer[:80] + '...') if len(obj.answer) > 80 else obj.answer
    short_answer.short_description = 'Answer'


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