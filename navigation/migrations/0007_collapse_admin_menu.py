"""Collapse the Admin menu to one entry per panel.

Repointing the old items left four of them ("Swims Admin", "Lessons Admin",
"Schools Admin", "Instructors Admin") all leading to /operations/, and Finance
had no entry at all — the only way in was typing the URL.

Three existing rows are renamed and repointed rather than deleted, so their
group and permission configuration survives; the redundant three are
deactivated rather than removed, so nothing is lost and the change reverses.
"""
from django.db import migrations

# label -> (new label, url_name, icon, order, required group names)
REPURPOSED = {
    "Swims Admin": ("Operations", "operations:index", "fas fa-clipboard-list", 0, []),
    "Users Admin": ("Settings", "settings:index", "fas fa-cog", 3, ["Manager"]),
}
NEW_FINANCE = ("Finance", "finance:index", "fas fa-euro-sign", 2, ["Manager", "Full-Timer"])
DEACTIVATE = ["Lessons Admin", "Schools Admin", "Instructors Admin", "General Administration"]


def collapse(apps, schema_editor):
    MenuItem = apps.get_model("navigation", "MenuItem")
    MenuGroup = apps.get_model("navigation", "MenuGroup")
    Group = apps.get_model("auth", "Group")

    admin_group = MenuGroup.objects.filter(name="Admin").first()
    if not admin_group:
        return

    def set_groups(item, names):
        item.required_groups.clear()
        for name in names:
            group = Group.objects.filter(name=name).first()
            if group:
                item.required_groups.add(group)

    for old_label, (label, url_name, icon, order, groups) in REPURPOSED.items():
        item = MenuItem.objects.filter(group=admin_group, label=old_label).first()
        if not item:
            continue
        item.label, item.url_name, item.icon_class, item.order = label, url_name, icon, order
        item.requires_login = item.requires_staff = True
        item.is_active = True
        item.save()
        set_groups(item, groups)

    label, url_name, icon, order, groups = NEW_FINANCE
    finance, _ = MenuItem.objects.get_or_create(
        group=admin_group, label=label,
        defaults={"url_name": url_name, "icon_class": icon, "order": order,
                  "requires_login": True, "requires_staff": True, "is_active": True},
    )
    finance.url_name, finance.icon_class, finance.order = url_name, icon, order
    finance.requires_login = finance.requires_staff = finance.is_active = True
    finance.save()
    set_groups(finance, groups)

    MenuItem.objects.filter(group=admin_group, label__in=DEACTIVATE).update(is_active=False)


def restore(apps, schema_editor):
    MenuItem = apps.get_model("navigation", "MenuItem")
    MenuGroup = apps.get_model("navigation", "MenuGroup")

    admin_group = MenuGroup.objects.filter(name="Admin").first()
    if not admin_group:
        return

    for old_label, (label, *_rest) in REPURPOSED.items():
        item = MenuItem.objects.filter(group=admin_group, label=label).first()
        if item:
            item.label = old_label
            item.required_groups.clear()
            item.save()

    MenuItem.objects.filter(group=admin_group, label="Finance").delete()
    MenuItem.objects.filter(group=admin_group, label__in=DEACTIVATE).update(is_active=True)


class Migration(migrations.Migration):

    dependencies = [("navigation", "0006_repoint_admin_menu_items")]

    operations = [migrations.RunPython(collapse, restore)]
