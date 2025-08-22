from django.core.management.base import BaseCommand
from navigation.models import MenuGroup, MenuItem
from django.contrib.auth.models import Group
from graphviz import Digraph

class Command(BaseCommand):
    help = "Export the navigation menu structure as a Graphviz diagram."

    def add_arguments(self, parser):
        parser.add_argument(
            "output_file",
            nargs="?",
            default="menu_graph",
            help="Base filename for the exported diagram (default: menu_graph)",
        )

    def handle(self, *args, **options):
        dot = Digraph(comment="Navigation Menu", format="png")

        # Draw groups (menu groups)
        for group in MenuGroup.objects.all().order_by("order"):
            dot.node(f"group_{group.id}", group.name,
                     shape="ellipse", style="filled", color="lightgreen")

            for item in MenuItem.objects.filter(group=group).order_by("order"):
                dot.node(f"item_{item.id}", item.label,
                         shape="note", style="filled", color="yellow")
                dot.edge(f"group_{group.id}", f"item_{item.id}")

                # Permission groups (Django auth groups)
                for g in item.required_groups.all():
                    dot.node(f"permgroup_{g.id}", g.name,
                             shape="box", style="filled", color="lightblue")
                    dot.edge(f"permgroup_{g.id}", f"item_{item.id}")

        output_file = options["output_file"]
        dot.render(output_file, cleanup=True)

        self.stdout.write(self.style.SUCCESS(f"✅ Navigation menu graph exported to {output_file}.png"))

# python manage.py download_navigation_menu_graph
