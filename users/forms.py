from django import forms
from allauth.account.forms import SignupForm
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models import  Swimling
from phonenumber_field.formfields import PhoneNumberField
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

# Get the custom user model
User = get_user_model()


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    lessons = forms.BooleanField(label="I wish to sign up for swimming lessons.",
                                 required=False)
    phone_number = PhoneNumberField(region='IE', required=True, label="Phone Number", help_text="Irish numbers only (e.g. 085..., 01..., or +353 ...)")
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['password1'].help_text = (
            "Must be 8+ characters, not too common or all numbers."
        )

    def clean_phone_number(self):
        number = self.cleaned_data.get('phone_number')
        # Ensure it is an Irish number only
        if not number:
            raise ValidationError("Phone number is required.")
        try:
            if getattr(number, 'country_code', None) != 353:
                raise ValidationError("Please enter an Irish phone number (+353 or 0...).")
        except Exception:
            raise ValidationError("Please enter a valid Irish phone number.")
        return number

    def save(self, request):
        # Call the parent save method to create the user instance
        user = super().save(request)

        # Persist phone number (Irish only) to user's mobile_phone
        phone = self.cleaned_data.get('phone_number')
        if phone:
            user.mobile_phone = phone
            user.save(update_fields=['mobile_phone'])

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
    mobile_phone = PhoneNumberField(
        region='IE',
        required=False,
        label="Phone Number",
        help_text="Irish numbers only (e.g. 085..., 01..., or +353 ...)",
    )

    class Meta:
        model = User
        fields = ("first_name", "last_name", "mobile_phone", "admin_notes")
        widgets = {
            "admin_notes": forms.Textarea(attrs={
                "rows": 4,
                "placeholder": "Add any personal notes or preferences...",
            }),
        }
        labels = {
            "mobile_phone": "Phone Number",
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
        self.fields['mobile_phone'].widget.attrs.update({
            'placeholder': 'Enter your phone number'
        })



class NewSwimlingForm(forms.ModelForm):
    class Meta:
        model = Swimling
        fields = ['first_name', 'last_name', 'dob', 'sco_role_num', 'notes']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date', 'required': True}),
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
