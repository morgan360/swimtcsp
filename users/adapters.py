from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.account.utils import perform_login
from allauth.exceptions import ImmediateHttpResponse
from django.http import HttpResponseRedirect
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
            perform_login(request, user, email_verification='optional')
            raise ImmediateHttpResponse(HttpResponseRedirect("/"))  # Or wherever you want
        except User.DoesNotExist:
            pass
