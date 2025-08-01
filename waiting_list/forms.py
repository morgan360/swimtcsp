from django import forms
from django.contrib.auth.models import User
from users.models import Swimling
from lessons.models import Product
from .models import WaitingList

from django import forms


class EmailOnlyForm(forms.Form):
    email = forms.EmailField(
        label="Your Email",
        widget=forms.EmailInput(attrs={
            "class": "w-full border border-gray-300 rounded p-2",
            "placeholder": "you@example.com"
        })
    )


class PublicWaitingListForm(forms.Form):
    email = forms.EmailField(label="Your Email")
    full_name = forms.CharField(label="Your Name", max_length=150)

    swimling = forms.ModelChoiceField(
        queryset=Swimling.objects.none(),
        required=False,
        label="Select a Swimling"
    )

    swimling_name = forms.CharField(label="Child's Name", max_length=100, required=False)
    swimling_dob = forms.DateField(label="Child's Date of Birth", widget=forms.DateInput(attrs={'type': 'date'}), required=False)

    is_transfer_request = forms.ChoiceField(
        choices=[(False, 'New Lesson'), (True, 'Transfer Request')],
        widget=forms.RadioSelect,
        label="Application Type"
    )

    preferred_lesson_1 = forms.ModelChoiceField(
        queryset=Product.objects.all(), label="1st Choice"
    )
    preferred_lesson_2 = forms.ModelChoiceField(
        queryset=Product.objects.all(), label="2nd Choice"
    )
    preferred_lesson_3 = forms.ModelChoiceField(
        queryset=Product.objects.all(), label="3rd Choice"
    )

    def __init__(self, *args, **kwargs):
        guardian = kwargs.pop('guardian', None)
        super().__init__(*args, **kwargs)

        if guardian:
            self.fields['swimling'].queryset = Swimling.objects.filter(guardian=guardian)
            self.fields['swimling'].required = True
            self.fields['swimling_name'].widget = forms.HiddenInput()
            self.fields['swimling_dob'].widget = forms.HiddenInput()
