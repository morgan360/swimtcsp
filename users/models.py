from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, \
    PermissionsMixin, Group
from django.db import models
from django.utils import timezone
from django.conf import settings
from phonenumber_field.modelfields import PhoneNumberField


class UserManager(BaseUserManager):
    def _create_user(self, email, password, is_staff, is_superuser, **extra_fields):
        if not email:
            raise ValueError('Users must have an email address')
        now = timezone.now()
        email = self.normalize_email(email)
        user = self.model(
            email=email,
            is_staff=is_staff,
            is_active=True,
            is_superuser=is_superuser,
            last_login=now,
            date_joined=now,
            **extra_fields
        )
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_user(self, email, password, **extra_fields):
        return self._create_user(email, password, False, False, **extra_fields)

    def create_superuser(self, email, password, **extra_fields):
        user = self._create_user(email, password, True, True, **extra_fields)
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    email = models.EmailField(max_length=254, unique=True)
    username = models.CharField(max_length=50, blank=True, null=True)
    first_name = models.CharField(max_length=150)
    last_name = models.CharField(max_length=254, null=True, blank=True)
    mobile_phone = PhoneNumberField(blank=True)
    other_phone = PhoneNumberField(blank=True)
    groups = models.ManyToManyField(Group, blank=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    is_active = models.BooleanField(default=True)
    last_login = models.DateTimeField(null=True, blank=True)
    date_joined = models.DateTimeField(auto_now_add=True)
    admin_notes = models.TextField(null=True, blank=True)
    # Set by users.retention after three years without a paid order, login or
    # visit; the personal details nobody needs any more are erased at the same
    # time. Cleared again if they log back in. Never use is_active for this:
    # that would lock out a parent who comes back.
    archived_at = models.DateTimeField(null=True, blank=True, db_index=True)
    # Set once the account has been anonymised, after six years or on request.
    anonymised_at = models.DateTimeField(null=True, blank=True)
    # Consent to marketing email, given by the tick-box at sign-up or on the
    # profile page. Only these accounts are copied to Mailchimp; see
    # mailchimp.services.sync_user.
    marketing_opt_in = models.BooleanField(
        default=False,
        verbose_name="News by email",
        help_text="Agreed to receive TCSP news and offers by email.",
    )
    marketing_opt_in_at = models.DateTimeField(null=True, blank=True)

    USERNAME_FIELD = 'email'
    EMAIL_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name']

    objects = UserManager()

    def __str__(self):
        name = f"{self.first_name or ''} {self.last_name or ''}".strip()
        # Prefer human name; fall back to email, then id
        return name or self.email or f"User {self.pk}"

    # Compatibility helpers often expected by Django/admin
    def get_full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    def get_short_name(self):
        return (self.first_name or '').strip() or self.email or str(self.pk)

    def get_absolute_url(self):
        return "/users/%i/" % (self.pk)


# One row per successful login. Django keeps only last_login, which cannot say
# how many people logged in yesterday or this week; the activity report needs this.
class LoginEvent(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="login_events")
    created = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"{self.user} at {self.created:%Y-%m-%d %H:%M}"


# One row per user per day they loaded any page while logged in. Sessions last
# while people keep using the site, so most visits never involve a login;
# written by utils.middleware.ActiveUserMiddleware.
class ActiveDay(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="active_days")
    date = models.DateField(db_index=True)

    class Meta:
        ordering = ["-date"]
        constraints = [models.UniqueConstraint(fields=["user", "date"], name="unique_user_active_day")]

    def __str__(self):
        return f"{self.user} on {self.date}"

class DataRetentionEvent(models.Model):
    """Audit trail for users.retention: what was done to which account, when.

    Holds no personal data on purpose — only the account id and the names of the
    fields that were cleared — so the log itself never needs erasing. user_id is
    a plain integer rather than a foreign key for the same reason.
    """
    ARCHIVED = "archived"
    UNARCHIVED = "unarchived"
    ANONYMISED = "anonymised"
    ERASED = "erased"
    ACTIONS = [
        (ARCHIVED, "Archived after 3 years inactive"),
        (UNARCHIVED, "Unarchived on login"),
        (ANONYMISED, "Anonymised after 6 years"),
        (ERASED, "Erased on request"),
    ]

    user_id = models.PositiveIntegerField(db_index=True)
    action = models.CharField(max_length=20, choices=ACTIONS)
    created = models.DateTimeField(auto_now_add=True, db_index=True)
    performed_by_id = models.PositiveIntegerField(
        null=True, blank=True, help_text="Staff account that asked for it; blank for the scheduled job.")
    detail = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-created"]

    def __str__(self):
        return f"User {self.user_id} {self.action} {self.created:%Y-%m-%d}"


# Stores the swimmer details with link to guardians
class Swimling(models.Model):
    guardian = models.ForeignKey(User, on_delete=models.CASCADE, blank=True,
                                 null=True)
    first_name = models.CharField(max_length=255)
    last_name = models.CharField(max_length=255, blank=True, null=True)
    dob = models.DateField(null=True, blank=False)
    sco_role_num = models.CharField(max_length=6, blank=True, null=True)
    notes = models.TextField(null=True, blank=True)
    # Kept apart from notes on purpose. `notes` is a general box guardians have
    # filled with all sorts over the years, and only medical information belongs
    # in front of a teacher at poolside, so only this field is printed on the
    # attendance sheet. Existing notes are deliberately left where they are
    # rather than migrated across: they are mostly not medical, and guessing
    # which ones are would put the wrong thing on a class list.
    medical_info = models.TextField(
        null=True,
        blank=True,
        verbose_name="Medical information",
        help_text="Anything a teacher needs to know at poolside, e.g. asthma, "
                  "epilepsy, allergies, or a hearing aid.",
    )
    wp_student_id = models.IntegerField(blank=True, null=True)

    def __str__(self):
        return f"{self.first_name} {self.last_name}"

# users/models.py

@property
def is_instructor(self):
    return self.groups.filter(name="instructor").exists()

@property
def is_assistant(self):
    return self.groups.filter(name="assistant").exists()
