# navigation/management/commands/load_navigation_menu.py

import json
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from navigation.models import MenuGroup, MenuItem


class Command(BaseCommand):
    help = "Import the navigation menu structure from a JSON file (opposite of download_navigation_menu)."

    def add_arguments(self, parser):
        parser.add_argument("json_file", type=str, help="Path to the JSON file containing the menu structure")

    def handle(self, *args, **options):
        json_file = options["json_file"]

        try:
            with open(json_file, "r") as f:
                menu_data = json.load(f)
        except FileNotFoundError:
            self.stderr.write(self.style.ERROR(f"❌ File not found: {json_file}"))
            return
        except json.JSONDecodeError as e:
            self.stderr.write(self.style.ERROR(f"❌ JSON decode error: {e}"))
            return

        # Clear existing menu
        MenuItem.objects.all().delete()
        MenuGroup.objects.all().delete()

        for group_entry in menu_data:
            group_info = group_entry["group"]
            items = group_entry.get("items", [])

            group = MenuGroup.objects.create(
                name=group_info["name"],
                slug=group_info["slug"],
                order=group_info["order"]
            )

            for item in items:
                menu_item = MenuItem.objects.create(
                    group=group,
                    label=item["label"],
                    url_name=item.get("url_name", ""),
                    external_url=item.get("external_url", ""),
                    icon_class=item.get("icon_class", ""),
                    order=item.get("order", 0),
                    requires_login=item.get("requires_login", False),
                    requires_staff=item.get("requires_staff", False),
                )

                for group_name in item.get("groups", []):
                    grp = Group.objects.get_or_create(name=group_name)[0]
                    menu_item.required_groups.add(grp)

        self.stdout.write(self.style.SUCCESS("✅ Navigation menu imported successfully."))
