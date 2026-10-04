# File that creats a default group for basic users.
# It is loaded in the apps.py

from django.contrib.auth.models import Group
from django.contrib.auth.signals import user_logged_in
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth import get_user_model
from django.urls import reverse

User = get_user_model()


@receiver(post_save, sender=User)
def add_default_group_to_user(sender, instance, created, **kwargs):
    if created:
        # Get or create the default group
        default_group, _ = Group.objects.get_or_create(name='Customer')
        # Add the default group to the user's groups
        instance.groups.add(default_group)


@receiver(user_logged_in)
def log_successful_login(sender, request, user, **kwargs):
    from users.models import LoginEvent

    # Hijack logs staff in as a customer (and back out) through login(), which
    # would otherwise count as that customer — and the staff member — logging in.
    if request is not None and request.path in (reverse('hijack:acquire'), reverse('hijack:release')):
        return
    LoginEvent.objects.create(user=user)