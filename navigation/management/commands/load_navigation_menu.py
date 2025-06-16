# navigation/management/commands/load_navigation_menu.py
from django.core.management.base import BaseCommand
from django.contrib.auth.models import Group
from navigation.models import MenuGroup, MenuItem
from django.urls import reverse, NoReverseMatch

class Command(BaseCommand):
    help = "Wipe and load the navigation menu from predefined structure."

    def handle(self, *args, **options):
        MenuItem.objects.all().delete()
        MenuGroup.objects.all().delete()

        def add_menu_group(name, slug):
            group, _ = MenuGroup.objects.get_or_create(name=name, slug=slug)
            return group

        def reverse_url(name):
            try:
                return reverse(name)
            except NoReverseMatch:
                return None

        def add_item(group, label, url_name=None, external_url=None, icon=None, order=0,
                     requires_login=False, requires_staff=False, groups=None):
            item = MenuItem.objects.create(
                group=group,
                label=label,
                url_name=url_name or '',
                external_url=external_url or '',
                icon_class=icon or '',
                order=order,
                requires_login=requires_login,
                requires_staff=requires_staff,
            )
            if groups:
                for g in groups:
                    grp = Group.objects.get_or_create(name=g)[0]
                    item.required_groups.add(grp)
            item.save()

        # === Public ===
        main = add_menu_group("Main", "main")
        add_item(main, "Home", url_name="home", order=1)
        add_item(main, "About", url_name="about", order=2)
        add_item(main, "Contact", url_name="contact", order=3)
        add_item(main, "Timetable", url_name="swims:product_list", icon="fas fa-calendar", order=4)

        # === Customer ===
        add_item(main, "Public Swims", url_name="swims:product_list", icon="fas fa-swimmer", order=5, requires_login=True)

        profile = add_menu_group("Profile", "profile")
        add_item(profile, "Manage Profile", url_name="users:profile", icon="fas fa-user-cog", order=1, requires_login=True)
        add_item(profile, "View Orders", url_name="swims_orders:order_list", icon="fas fa-receipt", order=2, requires_login=True)
        add_item(profile, "Upgrade to Guardian", url_name="users:upgrade_guardian", icon="fas fa-user-plus", order=3, requires_login=True)
        add_item(profile, "My Swim Bookings", url_name="swims:my_bookings", icon="fas fa-swimming-pool", order=4, requires_login=True, groups=["customer"])
        add_item(profile, "Logout", url_name="account_logout", icon="fas fa-sign-out-alt", order=5, requires_login=True)

        # === Guardian ===
        add_item(main, "Swimling Panel", url_name="users:combined_swimling_mgmt", icon="fas fa-user-friends", order=6, requires_login=True, groups=["guardian"])
        add_item(main, "Swimling Progress", url_name="lessons:swimling_progress", icon="fas fa-chart-line", order=7, requires_login=True, groups=["guardian"])
        add_item(main, "School Classes", url_name="schools:school_dashboard", icon="fas fa-school", order=8, requires_login=True, groups=["guardian", "schools"])

        # === School Users ===
        school = add_menu_group("School", "school")
        add_item(school, "Register School", url_name="school:register", icon="fas fa-plus", order=1, requires_login=True, groups=["schools"])
        add_item(school, "School Bookings", url_name="schools:school_list", icon="fas fa-calendar-check", order=2, requires_login=True, groups=["schools"])
        add_item(school, "School Dashboard", url_name="schools:school_dashboard", icon="fas fa-school", order=3, requires_login=True, groups=["schools"])

        # === Management ===
        management = add_menu_group("Management", "management")
        add_item(management, "Move Swimmers", url_name="management:move_swimmers", icon="fas fa-exchange-alt", order=1, requires_login=True, groups=["manager", "pool_manager"])
        add_item(management, "Order Management", url_name="management:order_list", icon="fas fa-box", order=2, requires_login=True, groups=["manager", "pool_manager"])

        # === Admin ===
        admin = add_menu_group("Admin", "admin")
        add_item(admin, "Admin Panel", external_url="/admin/", icon="fas fa-tools", order=1, requires_login=True, groups=["administrator"])
        add_item(admin, "Booking Management", url_name="lessons_bookings:management", icon="fas fa-calendar-alt", order=2, requires_login=True, groups=["administrator"])
        add_item(admin, "Analytics", url_name="reports:term_information", icon="fas fa-chart-line", order=3, requires_login=True, groups=["administrator"])
        add_item(admin, "Staff Schedule", url_name="staff:schedule", icon="fas fa-clock", order=4, requires_login=True, groups=["administrator"])
        add_item(admin, "Settings", url_name="settings", icon="fas fa-cog", order=5, requires_login=True, groups=["administrator"])

        # === Staff ===
        staff = add_menu_group("Staff", "staff")
        add_item(staff, "Staff Dashboard", url_name="staff:dashboard", icon="fas fa-tachometer-alt", order=1, requires_login=True, requires_staff=True)
        add_item(staff, "My Schedule", url_name="staff:schedule", icon="fas fa-clock", order=2, requires_login=True, requires_staff=True)
        add_item(staff, "Manage Bookings", url_name="lessons_bookings:management", icon="fas fa-calendar-check", order=3, requires_login=True, requires_staff=True)

        # === Reporting ===
        reporting = add_menu_group("Reporting", "reporting")
        add_item(reporting, "Enrollments", url_name="reports:enrollment_report", icon="fas fa-users", order=1, requires_login=True, requires_staff=True)
        add_item(reporting, "Class Lists", url_name="reports:class_list_view", icon="fas fa-list", order=2, requires_login=True, requires_staff=True)
        add_item(reporting, "Term Information", url_name="reports:term_information", icon="fas fa-calendar", order=3, requires_login=True, requires_staff=True)
        add_item(reporting, "All Reports", external_url="/reports/", icon="fas fa-tachometer-alt", order=4, requires_login=True, groups=["administrator"])

        self.stdout.write(self.style.SUCCESS("✅ Full navigation menu loaded successfully."))
