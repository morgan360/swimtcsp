# navigation/management/commands/download_navigation_menu.py

from django.core.management.base import BaseCommand
from navigation.models import MenuGroup, MenuItem

import json

class Command(BaseCommand):
    help = "Export the current navigation menu structure to JSON."

    def handle(self, *args, **options):
        output = []

        groups = MenuGroup.objects.all().order_by("order")

        for group in groups:
            group_data = {
                "group": {
                    "name": group.name,
                    "slug": group.slug,
                    "order": group.order,
                },
                "items": [],
            }

            items = MenuItem.objects.filter(group=group).order_by("order")

            for item in items:
                item_data = {
                    "label": item.label,
                    "url_name": item.url_name,
                    "external_url": item.external_url,
                    "icon_class": item.icon_class,
                    "order": item.order,
                    "requires_login": item.requires_login,
                    "requires_staff": item.requires_staff,
                    "groups": list(item.required_groups.values_list("name", flat=True)),
                }
                group_data["items"].append(item_data)

            output.append(group_data)

        self.stdout.write(json.dumps(output, indent=2))
        self.stdout.write(self.style.SUCCESS("✅ Navigation menu exported successfully."))
