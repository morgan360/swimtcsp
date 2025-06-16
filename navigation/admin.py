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
class MenuItemAdmin(admin.ModelAdmin):  # ← Renamed from MenuItemInline
    list_display = ("label", "group", "url_name", "external_url", "order", "requires_login", "requires_staff")
    list_filter = ("group", "requires_login", "requires_staff")
    ordering = ("group", "order")
    filter_horizontal = ("required_groups",)
    search_fields = ("label", "url_name", "external_url")
