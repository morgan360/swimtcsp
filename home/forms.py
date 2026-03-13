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

    # Honeypot field - hidden from humans, bots will fill it in
    website = forms.CharField(
        required=False,
        widget=forms.HiddenInput(attrs={'tabindex': '-1', 'autocomplete': 'off'}),
    )

    def clean_website(self):
        """Reject submissions where the honeypot field is filled in."""
        if self.cleaned_data.get('website'):
            raise ValidationError('Spam detected.')
        return ''

    def clean_message(self):
        """Basic spam content checks."""
        message = self.cleaned_data.get('message', '')

        # Reject messages with excessive URLs (3+)
        url_count = len(re.findall(r'https?://', message))
        if url_count >= 3:
            raise ValidationError('Your message contains too many links.')

        return message