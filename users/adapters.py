# This is the file that contains the adapters for allauth to work with our custom user model, so that we cann link
# social accounts to existing accounts in our user model.
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.app_settings import EmailVerificationMethod
from allauth.account.stages import EmailVerificationStage
from allauth.account.utils import perform_login
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.internal.flows.login import record_authentication
from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


def google_verified_email(account):
    """The address a Google SocialAccount says Google has verified, lower-cased, or ''."""
    data = account.extra_data or {}
    if data.get("email_verified") or data.get("verified_email"):
        return (data.get("email") or "").lower()
    return ""


def email_confirmed(user):
    """
    Has the user confirmed the address they sign in with?

    Signing in with Google counts when Google says it has verified that same
    address. AutoLinkSocialAccountAdapter links Google to existing accounts
    without allauth ever recording the address as verified, so 588 of the
    1,126 Google accounts on 2026-10-28 had no record of it. The first time
    one is found here it is recorded, so the check is a single query after.
    """
    from allauth.account.models import EmailAddress
    from allauth.socialaccount.models import SocialAccount

    if EmailAddress.objects.filter(user=user, email__iexact=user.email, verified=True).exists():
        return True
    for account in SocialAccount.objects.filter(user=user, provider="google"):
        if google_verified_email(account) == user.email.lower():
            address = EmailAddress.objects.filter(user=user, email__iexact=user.email).first()
            if address:
                address.verified = True
                address.save(update_fields=["verified"])
            else:
                EmailAddress.objects.create(
                    user=user,
                    email=user.email,
                    verified=True,
                    primary=not EmailAddress.objects.filter(user=user, primary=True).exists(),
                )
            return True
    return False


class NewAccountEmailVerificationStage(EmailVerificationStage):
    """
    Make accounts created from TCSP_EMAIL_VERIFICATION_FROM onwards verify
    their email before they can sign in.

    Setting ACCOUNT_EMAIL_VERIFICATION to "mandatory" would do this for every
    account, and most existing customers have never verified theirs: they would
    all be stopped at their next login. Older accounts keep the site-wide
    setting instead.
    """

    def handle(self):
        cutoff = settings.TCSP_EMAIL_VERIFICATION_FROM
        if cutoff and self.login.user.date_joined >= cutoff:
            self.login.email_verification = EmailVerificationMethod.MANDATORY
        return super().handle()


# Throwaway inboxes anyone can read. On 22 Nov 2026 an attack script signed up
# with mailnesia.com and "verified" through its public inbox. No real customer
# used any of these on that date (one account in all, the script's). Proton and
# similar private services are real mailboxes and stay allowed.
DISPOSABLE_EMAIL_DOMAINS = frozenset("""
    mailnesia.com mailinator.com guerrillamail.com guerrillamail.net guerrillamail.org
    guerrillamailblock.com sharklasers.com grr.la pokemail.net spam4.me yopmail.com
    yopmail.fr yopmail.net 10minutemail.com 10minutemail.net temp-mail.org tempmail.com
    tempmail.net tempmailo.com tempr.email trashmail.com trashmail.de trashmail.net
    getnada.com nada.email maildrop.cc dispostable.com throwawaymail.com mohmal.com
    emailondeck.com mintemail.com fakeinbox.com mailcatch.com mytemp.email tempinbox.com
    burnermail.io spamgourmet.com mailpoof.com moakt.com mail.tm mail.gw inboxkitten.com
    emailfake.com fakemail.net discard.email mailsac.com tmail.ws tmpmail.org tmpmail.net
    1secmail.com 1secmail.org 1secmail.net
""".split())

DISPOSABLE_EMAIL_MESSAGE = (
    "Please use your own email address. We send booking confirmations and "
    "class updates there, so temporary inboxes can't be used."
)


def is_disposable_email(email):
    domain = (email or "").rsplit("@", 1)[-1].strip().lower().rstrip(".")
    parts = domain.split(".")
    # The domain itself or any parent of it: x.mailinator.com counts too.
    return any(".".join(parts[i:]) in DISPOSABLE_EMAIL_DOMAINS for i in range(len(parts) - 1))


class AccountAdapter(DefaultAccountAdapter):
    def clean_email(self, email):
        """Runs on sign-up and when adding or changing an email address."""
        email = super().clean_email(email)
        if is_disposable_email(email):
            raise ValidationError(DISPOSABLE_EMAIL_MESSAGE)
        return email

    def get_login_stages(self):
        return [
            "users.adapters.NewAccountEmailVerificationStage"
            if stage == "allauth.account.stages.EmailVerificationStage"
            else stage
            for stage in super().get_login_stages()
        ]

class AutoLinkSocialAccountAdapter(DefaultSocialAccountAdapter):
    def pre_social_login(self, request, sociallogin):
        if request.user.is_authenticated:
            return

        email = sociallogin.account.extra_data.get('email')
        if not email:
            return

        try:
            user = User.objects.get(email=email)
            # Link and log in
            sociallogin.connect(request, user)
            # Hand back perform_login's own response: when the account has
            # two-factor on, it is the redirect to the code prompt, and the user
            # is not logged in until they get past it. Redirecting to "/" here
            # instead would drop them there silently logged out.
            # allauth's own social login records "signed in with Google just
            # now" before logging in; going straight to perform_login skipped
            # that, so allauth treated every Google login as stale and asked for
            # the password again before letting anyone set up two-factor.
            record_authentication(request, sociallogin)
            response = perform_login(request, user, email_verification='optional')
            raise ImmediateHttpResponse(response)
        except User.DoesNotExist:
            pass
