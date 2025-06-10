from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group

User = get_user_model()


class Command(BaseCommand):
    help = 'Creates test users with specific group assignments'

    def handle(self, *args, **options):
        # Create or get the necessary groups
        customer_group, _ = Group.objects.get_or_create(name='Customer')
        guardian_group, _ = Group.objects.get_or_create(name='Guardian')
        bishopgalvin_group, _ = Group.objects.get_or_create(name='bishopgalvin')
        zion_group, _ = Group.objects.get_or_create(name='zion')

        # Create test users

        # 1. Public user (Customer group only)
        public_user, created = User.objects.get_or_create(
            email='public@acme.ie',
            defaults={
                'first_name': 'Public',
                'last_name': 'User',
                'is_active': True,
            }
        )

        if created:
            public_user.set_password('public1234')
            public_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created public user: {public_user.email}'))
        else:
            self.stdout.write(self.style.WARNING(f'User {public_user.email} already exists'))

        # Ensure public user is only in the Customer group
        public_user.groups.clear()  # Remove from all groups first
        public_user.groups.add(customer_group)

        # 2. Guardian user (Customer and Guardian groups)
        guardian_user, created = User.objects.get_or_create(
            email='guardian@acme.ie',
            defaults={
                'first_name': 'Guardian',
                'last_name': 'Parent',
                'is_active': True,
            }
        )

        if created:
            guardian_user.set_password('guardian1234')
            guardian_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created guardian user: {guardian_user.email}'))
        else:
            self.stdout.write(self.style.WARNING(f'User {guardian_user.email} already exists'))

        # Ensure guardian user is in both Customer and Guardian groups
        guardian_user.groups.clear()
        guardian_user.groups.add(customer_group, guardian_group)

        # 3. Bishop Galvin School user
        bishopgalvin_user, created = User.objects.get_or_create(
            email='bishopgalvin@acme.ie',
            defaults={
                'first_name': 'Bishop',
                'last_name': 'Galvin',
                'is_active': True,
            }
        )

        if created:
            bishopgalvin_user.set_password('bishopgalvin1234')
            bishopgalvin_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created Bishop Galvin user: {bishopgalvin_user.email}'))
        else:
            self.stdout.write(self.style.WARNING(f'User {bishopgalvin_user.email} already exists'))

        # Ensure Bishop Galvin user is in Customer and bishopgalvin groups
        bishopgalvin_user.groups.clear()
        bishopgalvin_user.groups.add(customer_group, bishopgalvin_group)

        # 4. Zion School user
        zion_user, created = User.objects.get_or_create(
            email='zion@acme.ie',
            defaults={
                'first_name': 'Zion',
                'last_name': 'School',
                'is_active': True,
            }
        )

        if created:
            zion_user.set_password('zion1234')
            zion_user.save()
            self.stdout.write(self.style.SUCCESS(f'Created Zion user: {zion_user.email}'))
        else:
            self.stdout.write(self.style.WARNING(f'User {zion_user.email} already exists'))

        # Ensure Zion user is in Customer and zion groups
        zion_user.groups.clear()
        zion_user.groups.add(customer_group, zion_group)

        self.stdout.write(self.style.SUCCESS('All test users have been created successfully'))