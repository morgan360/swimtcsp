from django import forms
from users.models import Swimling


class CartAddProductForm(forms.Form):
    swimling = forms.ModelChoiceField(
        queryset=Swimling.objects.none(),
        label="Select a swimling",
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        print("User:", user)
        queryset = Swimling.objects.filter(guardian=user)
        print("Queryset:", queryset)
        self.fields['swimling'].queryset = queryset


from django import forms

class NewSwimlingForm(forms.ModelForm):
    class Meta:
        model = Swimling
        fields = ['first_name', 'last_name', 'dob', 'sco_role_num', 'notes']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date'}),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'dob': 'Date of Birth',
            'sco_role_num': 'School Role Number',
            'notes': 'Additional Notes'
        }

