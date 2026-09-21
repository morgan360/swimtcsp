"""Point the admin menu items at the consolidated panels.

MenuItem.resolve_url() returns "#" when reverse() fails, so a stale url_name
becomes a link that silently does nothing rather than an error anyone notices.
The nine admin panels became three, which left six items dead.

Only the six known-dead admin names are touched, and the migration reverses
cleanly. Other dead entries in this table (staff:*, management:*, and a few
others) predate this change and are left alone — they are a separate question.
"""
from django.db import migrations

# old url_name -> new url_name
REPOINTED = {
    "swimsadmin:index": "operations:index",
    "lessonsadmin:index": "operations:index",
    "schoolsadmin:index": "operations:index",
    "instructorsadmin:index": "operations:index",
    "usersadmin:index": "settings:index",
    "generaladmin:index": "settings:index",
}


def repoint(apps, schema_editor):
    MenuItem = apps.get_model("navigation", "MenuItem")
    for old, new in REPOINTED.items():
        MenuItem.objects.filter(url_name=old).update(url_name=new)


def unpoint(apps, schema_editor):
    """Restore by label, since several old names map onto one new one."""
    MenuItem = apps.get_model("navigation", "MenuItem")
    by_label = {
        "Swims Admin": "swimsadmin:index",
        "Lessons Admin": "lessonsadmin:index",
        "Schools Admin": "schoolsadmin:index",
        "Instructors Admin": "instructorsadmin:index",
        "Users Admin": "usersadmin:index",
        "General Administration": "generaladmin:index",
    }
    for label, old in by_label.items():
        MenuItem.objects.filter(
            label=label, url_name__in=("operations:index", "settings:index")
        ).update(url_name=old)


class Migration(migrations.Migration):

    dependencies = [("navigation", "0005_menuitem_excluded_groups")]

    operations = [migrations.RunPython(repoint, unpoint)]
