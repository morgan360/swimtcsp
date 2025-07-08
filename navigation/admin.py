from django.contrib import admin
from .models import MenuGroup, MenuItem


class MenuItemInline(admin.StackedInline):  # ← Changed to StackedInline
    model = MenuItem
    extra = 1
    filter_horizontal = ("required_groups",)


@admin.register(MenuGroup)
class MenuGroupAdmin(admin.ModelAdmin):
    list_display = ("name", "slug", "order")
    prepopulated_fields = {"slug": ("name",)}
    inlines = [MenuItemInline]


@admin.register(MenuItem)
class MenuItemAdmin(admin.ModelAdmin):
    list_display = ('label', 'is_active', 'group', 'url_name', 'requires_login', 'requires_staff')
    list_editable = ('is_active',)  # 👈 Allows editing is_active inline
    list_display_links = ('label',)  # 👈 Makes 'label' the clickable link to edit detail view
    list_filter = ('group', 'is_active', 'requires_login', 'requires_staff')
    search_fields = ('label', 'url_name', 'external_url')
