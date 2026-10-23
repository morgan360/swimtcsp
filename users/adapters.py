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

User = get_user_model()


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


class AccountAdapter(DefaultAccountAdapter):
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
