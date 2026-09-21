"""Put Admin Dashboard at the top of the Admin menu.

It is the page staff open most often, so it should not sit second behind a
panel. Ordering only — nothing is added, removed or repointed.
"""
from django.db import migrations

# label -> order, lowest first (MenuItem.Meta.ordering is ["order"])
NEW_ORDER = {
    "Admin Dashboard": 0,
    "Operations": 1,
    "Finance": 2,
    "Settings": 3,
}
PREVIOUS_ORDER = {
    "Operations": 0,
    "Admin Dashboard": 1,
    "Finance": 2,
    "Settings": 3,
}


def _apply(apps, order_map):
    MenuItem = apps.get_model("navigation", "MenuItem")
    MenuGroup = apps.get_model("navigation", "MenuGroup")
    admin_group = MenuGroup.objects.filter(name="Admin").first()
    if not admin_group:
        return
    for label, order in order_map.items():
        MenuItem.objects.filter(group=admin_group, label=label).update(order=order)


def forwards(apps, schema_editor):
    _apply(apps, NEW_ORDER)


def backwards(apps, schema_editor):
    _apply(apps, PREVIOUS_ORDER)


class Migration(migrations.Migration):

    dependencies = [("navigation", "0007_collapse_admin_menu")]

    operations = [migrations.RunPython(forwards, backwards)]
