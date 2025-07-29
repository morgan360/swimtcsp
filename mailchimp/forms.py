# mailchimp/forms.py
from django import forms

class TestCampaignForm(forms.Form):
    email = forms.EmailField(label="Test Email", required=True)

class NewsletterSignupForm(forms.Form):
    email = forms.EmailField(label="", widget=forms.EmailInput(attrs={
        "placeholder": "Enter your email",
        "class": "input",  # or Tailwind: "form-input"
    }))