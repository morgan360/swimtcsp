from django import forms
from allauth.account.forms import SignupForm
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models import UserProfile, Swimling

# Get the custom user model
User = get_user_model()


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150, required=True)
    lessons = forms.BooleanField(label="I wish to apply for children's lessons",
                                 required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
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


# Update Profile - NOW WITH USERNAME
class UserForm(forms.ModelForm):
    class Meta:
        model = User
        fields = ("username", "first_name", "last_name")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Add help text and styling
        self.fields['username'].help_text = (
            "Required. 150 characters or fewer. Letters, digits and @/./+/-/_ only."
        )
        self.fields['username'].widget.attrs.update({
            'placeholder': 'Enter your username'
        })
        self.fields['first_name'].widget.attrs.update({
            'placeholder': 'Enter your first name'
        })
        self.fields['last_name'].widget.attrs.update({
            'placeholder': 'Enter your last name'
        })

    def clean_username(self):
        """Ensure username is unique (excluding current user)"""
        username = self.cleaned_data['username']

        # Get the current user instance
        user_id = self.instance.pk if self.instance else None

        # Check if username exists for other users
        if User.objects.filter(username=username).exclude(pk=user_id).exists():
            raise forms.ValidationError("A user with that username already exists.")

        return username


class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ('notes',)
        widgets = {
            'notes': forms.Textarea(attrs={
                'rows': 4,
                'placeholder': 'Add any personal notes or preferences...'
            }),
        }


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