from ckeditor.fields import RichTextField
from django.db import models
from django.utils import timezone


class Announcement(models.Model):
    """A single notice shown on the home page. Newest active one wins."""

    title = models.CharField(max_length=200)
    body = RichTextField(blank=True, help_text="Optional. One or two sentences.")
    link_url = models.URLField(blank=True, help_text="Optional. Where the button goes.")
    link_text = models.CharField(
        max_length=60, blank=True, help_text="Button label, e.g. 'Book now'."
    )
    is_active = models.BooleanField(
        default=False, help_text="Tick to show on the home page."
    )
    expires_on = models.DateField(
        null=True,
        blank=True,
        help_text=(
            "Optional. Last day the notice is shown — it disappears by itself "
            "the morning after. Leave blank to show until you untick 'Is active'."
        ),
    )
    created = models.DateTimeField(auto_now_add=True)
    updated = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated"]
        verbose_name = "Home page notice"

    def __str__(self):
        return self.title

    @property
    def has_expired(self):
        # localdate(), not now().date(): the site runs on Europe/Dublin, so
        # during Irish Summer Time a UTC date would roll the notice over an
        # hour early.
        return self.expires_on is not None and self.expires_on < timezone.localdate()

    @classmethod
    def current(cls):
        # Ticking a second notice active does not untick the first; the most
        # recently updated one simply wins, so there is no hidden side effect
        # on save. A blank expires_on never expires; a set one is the last day
        # shown, inclusive.
        return (
            cls.objects.filter(is_active=True)
            .filter(
                models.Q(expires_on__isnull=True)
                | models.Q(expires_on__gte=timezone.localdate())
            )
            .first()
        )
