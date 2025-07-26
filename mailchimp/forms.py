# mailchimp/forms.py
from django import forms

class TestCampaignForm(forms.Form):
    email = forms.EmailField(label="Test Email", required=True)

