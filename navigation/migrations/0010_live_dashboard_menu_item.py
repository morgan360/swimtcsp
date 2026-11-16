"""Give the Live Dashboard its own entry in the Admin menu.

It was reachable only from a link on the Finance index and the "Full dashboard"
link on the Operations and staff homes. It goes second, straight after "Admin
Dashboard", and is shown to the same people the page admits: Managers and
Full-Timers (superusers see every item).
"""
from django.db import migrations

LABEL = "Live Dashboard"
GROUPS = ["Manager", "Full-Timer"]
NEW_ORDER = {"Operations": 2, "Lessons Admin": 3, "Swims Admin": 4, "Schools Admin": 5,
             "Finance": 6, "Settings": 7}
PREVIOUS_ORDER = {"Operations": 1, "Lessons Admin": 2, "Swims Admin": 3, "Schools Admin": 4,
                  "Finance": 5, "Settings": 6}


def forwards(apps, schema_editor):
    MenuItem = apps.get_model("navigation", "MenuItem")
    MenuGroup = apps.get_model("navigation", "MenuGroup")
    Group = apps.get_model("auth", "Group")
    admin_group = MenuGroup.objects.filter(name="Admin").first()
    if not admin_group:
        return

    item = MenuItem.objects.filter(group=admin_group, label=LABEL).first()
    if item is None:
        item = MenuItem(group=admin_group, label=LABEL)
    item.url_name, item.external_url = "finance:dashboard", ""
    item.icon_class, item.order = "fas fa-chart-line", 1
    item.requires_login = item.requires_staff = item.is_active = True
    item.save()
    item.required_groups.set(Group.objects.filter(name__in=GROUPS))

    for label, order in NEW_ORDER.items():
        MenuItem.objects.filter(group=admin_group, label=label).update(order=order)


def backwards(apps, schema_editor):
    MenuItem = apps.get_model("navigation", "MenuItem")
    MenuGroup = apps.get_model("navigation", "MenuGroup")
    admin_group = MenuGroup.objects.filter(name="Admin").first()
    if not admin_group:
        return

    MenuItem.objects.filter(group=admin_group, label=LABEL).delete()
    for label, order in PREVIOUS_ORDER.items():
        MenuItem.objects.filter(group=admin_group, label=label).update(order=order)


class Migration(migrations.Migration):

    dependencies = [("navigation", "0009_admin_menu_sections"),
                    ("auth", "0012_alter_user_first_name_max_length")]

    operations = [migrations.RunPython(forwards, backwards)]
