# navigation/models.py
from django.db import models
from django.contrib.auth.models import Group
from django.urls import reverse_lazy


class MenuGroup(models.Model):
    name = models.CharField(max_length=100)
    slug = models.SlugField(unique=True)
    order = models.PositiveIntegerField(default=0)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ["order", "name"]

class MenuItem(models.Model):
    # Add this field to MenuItem
    is_active = models.BooleanField(default=True, help_text="Uncheck to hide this menu item.")
    group = models.ForeignKey(MenuGroup, on_delete=models.CASCADE, related_name='items')
    label = models.CharField(max_length=100)
    url_name = models.CharField(max_length=100, blank=True, help_text="Name of a Django URL pattern")
    external_url = models.CharField(
        max_length=200,
        blank=True,
        help_text="Used only if url_name is not set. Accepts relative or absolute URLs."
    )
    icon_class = models.CharField(max_length=50, blank=True, help_text="FontAwesome or custom icon class")
    order = models.PositiveIntegerField(default=0)
    requires_login = models.BooleanField(default=False)
    requires_staff = models.BooleanField(default=False)
    required_groups = models.ManyToManyField(Group, blank=True)

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return f"{self.label} ({self.group.name})"

    def resolve_url(self):
        from django.urls import reverse, NoReverseMatch
        if self.url_name:
            try:
                return reverse(self.url_name)
            except NoReverseMatch:
                return "#"
        return self.external_url or "#"
