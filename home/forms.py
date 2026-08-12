# forms.py
import re
from django import forms
from django.core.exceptions import ValidationError
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox


class ContactForm(forms.Form):
    name = forms.CharField(max_length=100)
    email = forms.EmailField()
    subject = forms.CharField(max_length=200)
    message = forms.CharField(widget=forms.Textarea)
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    # Honeypot field - hidden from humans, bots will fill it in.
    # Deliberately left un-cleaned: info_view reads this value to decide whether
    # to fake success, so the form must pass it through as submitted. It used to
    # have a clean_website() that raised ValidationError, which defeated that
    # twice over — the form came back invalid, so the view never got to look,
    # and the bot was told "Spam detected." instead of being quietly dropped.
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}),
    )

    def clean_message(self):
        """Basic spam content checks."""
        message = self.cleaned_data.get('message', '')

        # Reject messages with excessive URLs (3+)
        url_count = len(re.findall(r'https?://', message))
        if url_count >= 3:
            raise ValidationError('Your message contains too many links.')

        return message