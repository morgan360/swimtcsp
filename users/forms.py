from django import forms
from allauth.account.forms import SignupForm
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models import  Swimling

# Get the custom user model
User = get_user_model()


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    lessons = forms.BooleanField(label="I wish to sign up for swimming lessons.",
                                 required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['password1'].help_text = (
            "Must be 8+ characters, not too common or all numbers."
        )

    def save(self, request):
        # Call the parent save method to create the user instance
        user = super().save(request)

        # Check if the 'lessons' checkbox is checked
        if self.cleaned_data.get('lessons', False):
            # Replace 'Guardian' with the name of the group you want to assign the user to
            group_name = 'Guardian'
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

        # Return the user instance
        return user


# Update Profile - NO USERNAME
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("first_name", "last_name", "admin_notes")
        widgets = {
            "admin_notes": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Add any personal notes or preferences...",
            }),
        }
        labels = {
            "admin_notes": "Notes",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add placeholders for displayed fields
        self.fields['first_name'].widget.attrs.update({
            'placeholder': 'Enter your first name'
        })
        self.fields['last_name'].widget.attrs.update({
            'placeholder': 'Enter your last name'
        })



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

class GuardianOptInForm(forms.Form):
    become_guardian = forms.BooleanField(label="I would like to become a guardian", required=True)


class JoinSchoolsForm(forms.Form):
    join_schools = forms.BooleanField(
        label="I want to join the Schools Program",
        required=True
    )
