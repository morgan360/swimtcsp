# This is the file that contains the adapters for allauth to work with our custom user model, so that we cann link
# social accounts to existing accounts in our user model.
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login
from allauth.core.exceptions import ImmediateHttpResponse
from django.contrib.auth import get_user_model

User = get_user_model()

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
            response = perform_login(request, user, email_verification='optional')
            raise ImmediateHttpResponse(response)
        except User.DoesNotExist:
            pass
