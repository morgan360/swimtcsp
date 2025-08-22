from django.core.management.base import BaseCommand
from navigation.models import MenuGroup, MenuItem
import pandas as pd

class Command(BaseCommand):
    help = "Export the navigation menu structure to an Excel file."

    def add_arguments(self, parser):
        parser.add_argument(
            "output_file",
            nargs="?",
            default="menu_export.xlsx",
            help="File to save the exported menu (default: menu_export.xlsx)",
        )

    def handle(self, *args, **options):
        data = []

        groups = MenuGroup.objects.all().order_by("order")

        for group in groups:
            items = MenuItem.objects.filter(group=group).order_by("order")
            for item in items:
                required_groups = ", ".join(item.required_groups.values_list("name", flat=True))
                data.append({
                    "Menu Group": group.name,
                    "Menu Item": item.label,
                    "Required Groups": required_groups if required_groups else "—",
                })

        df = pd.DataFrame(data)
        df.to_excel(options["output_file"], index=False)

        self.stdout.write(
            self.style.SUCCESS(f"✅ Navigation menu exported to {options['output_file']}")
        )

# python manage.py navigation_menu_excel