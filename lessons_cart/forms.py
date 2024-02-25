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
