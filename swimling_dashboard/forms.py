from django import forms
from users.models import Swimling

class SwimlingForm(forms.ModelForm):
    class Meta:
        model = Swimling
        fields = ['first_name', 'last_name', 'dob', 'sco_role_num', 'notes']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
        }

class SwimlingForm(forms.ModelForm):
    class Meta:
        model = Swimling
        fields = ['first_name', 'last_name', 'dob', 'sco_role_num', 'notes']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Add any relevant swimling information here...',
            }),
        }