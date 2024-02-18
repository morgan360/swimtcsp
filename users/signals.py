# File that creats a default group for basic users.
# It is loaded in the apps.py

from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from .models import UserProfile
from django.utils.timezone import now

User = get_user_model()


@receiver(post_save, sender=User)
def add_default_group_to_user(sender, instance, created, **kwargs):
    if created:
        # Get or create the default group
        default_group, _ = Group.objects.get_or_create(name='Customer')
        # UserProfile.objects.create(user=instance)
        # Add the default group to the user's groups
        instance.groups.add(default_group)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        UserProfile.objects.create(user=instance)


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    User = get_user_model()
    # Determine the identifier field dynamically
    identifier_field = getattr(User, 'USERNAME_FIELD', 'username')
    identifier = getattr(user, identifier_field, 'Unknown')

    print(f"Successful login for: {identifier} at {now()}")