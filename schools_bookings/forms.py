# forms.py
from django import forms
from django.forms import formset_factory
from django.contrib.auth.forms import UserCreationForm
from users.models import Swimling, User
from django.contrib.auth import get_user_model
from schools.models import ScoLessons

class DirectOrderForm(forms.Form):
    lesson = forms.ModelChoiceField(
        queryset=ScoLessons.objects.none(),
        label="Select a Lesson",
        widget=forms.Select(attrs={'class': 'select is-primary'})
    )

    def __init__(self, *args, lessons=None, **kwargs):
        super().__init__(*args, **kwargs)
        if lessons is not None:
            self.fields['lesson'].queryset = lessons


# Define a form to ask if the user wants to add another swimling
class AddAnotherSwimlingForm(forms.Form):
    add_another = forms.BooleanField(
        label="Do you want to register another swimling?",
        required=False
    )


class UserRegistrationForm(UserCreationForm):
    class Meta:
        model = get_user_model()
        fields = ['first_name', 'last_name', 'email', 'mobile_phone']


# Password fields are inherited

class SwimlingRegistrationForm(forms.ModelForm):
    class Meta:
        model = Swimling
        fields = ['first_name', 'last_name']

    def __init__(self, *args, **kwargs):
        super(SwimlingRegistrationForm, self).__init__(*args, **kwargs)
        self.fields['first_name'].widget.attrs.update({'class': 'form-control'})
        self.fields['last_name'].widget.attrs.update({'class': 'form-control'})


