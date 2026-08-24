from django import forms
from users.models import Swimling

# There were two SwimlingForm classes defined here, identical but for the notes
# widget. The second silently replaced the first, so the first had never been
# used by anything. Only the one that was actually in effect is kept.


class SwimlingForm(forms.ModelForm):
    class Meta:
        model = Swimling
        fields = ['first_name', 'last_name', 'dob', 'sco_role_num', 'medical_info', 'notes']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'medical_info': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g. asthma, epilepsy, allergies, hearing aid. '
                               'Leave blank if there is nothing.',
            }),
            'notes': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'Anything else you would like us to know.',
            }),
        }
        labels = {
            'medical_info': 'Medical information',
            'notes': 'Other notes',
        }
        help_texts = {
            # Said plainly, because this is the one field a teacher reads at
            # poolside and the distinction is what keeps the rest off the sheet.
            'medical_info': 'This is shown to your child\'s teacher. Please put '
                            'anything they need to know here.',
            'notes': 'Not shown to teachers.',
        }
