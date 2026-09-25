"""Bring Lessons, Swims and Schools back to the Admin menu.

Staff who work mostly in the back end missed going straight to their area from
the menu. Each entry now opens that section of Operations rather than a panel
of its own. "Lessons Admin" and "Schools Admin" were deactivated by 0007 and are
switched back on; the old "Swims Admin" row became "Operations", so Swims gets a
new row.
"""
from django.db import migrations

# label -> (section URL, icon, order)
SECTIONS = {
    "Lessons Admin": ("/operations/section/lessons/", "fas fa-graduation-cap", 2),
    "Swims Admin": ("/operations/section/swims/", "fas fa-swimmer", 3),
    "Schools Admin": ("/operations/section/schools/", "fas fa-school", 4),
}
NEW_ORDER = {"Finance": 5, "Settings": 6}
PREVIOUS_ORDER = {"Finance": 2, "Settings": 3}


def forwards(apps, schema_editor):
    MenuItem = apps.get_model("navigation", "MenuItem")
    MenuGroup = apps.get_model("navigation", "MenuGroup")
    admin_group = MenuGroup.objects.filter(name="Admin").first()
    if not admin_group:
        return

    for label, (url, icon, order) in SECTIONS.items():
        item = MenuItem.objects.filter(group=admin_group, label=label).first()
        if item is None:
            item = MenuItem(group=admin_group, label=label)
        item.url_name, item.external_url = "", url
        item.icon_class, item.order = icon, order
        item.requires_login = item.requires_staff = item.is_active = True
        item.save()

    for label, order in NEW_ORDER.items():
        MenuItem.objects.filter(group=admin_group, label=label).update(order=order)


def backwards(apps, schema_editor):
    MenuItem = apps.get_model("navigation", "MenuItem")
    MenuGroup = apps.get_model("navigation", "MenuGroup")
    admin_group = MenuGroup.objects.filter(name="Admin").first()
    if not admin_group:
        return

    MenuItem.objects.filter(group=admin_group, label="Swims Admin").delete()
    MenuItem.objects.filter(group=admin_group, label__in=["Lessons Admin", "Schools Admin"]).update(
        is_active=False, url_name="operations:index", external_url="")
    for label, order in PREVIOUS_ORDER.items():
        MenuItem.objects.filter(group=admin_group, label=label).update(order=order)


class Migration(migrations.Migration):

    dependencies = [("navigation", "0008_admin_dashboard_first")]

    operations = [migrations.RunPython(forwards, backwards)]
