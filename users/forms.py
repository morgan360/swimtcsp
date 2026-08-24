from django import forms
from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.core.exceptions import ValidationError
from django.contrib.auth.models import Group
from django.contrib.auth import get_user_model
from .models import  Swimling
from phonenumber_field.formfields import PhoneNumberField
from django_recaptcha.fields import ReCaptchaField
from django_recaptcha.widgets import ReCaptchaV2Checkbox

# Get the custom user model
User = get_user_model()


def irish_phone_field():
    """The signup phone field, built here so both signup paths share one definition.

    A function rather than an attribute on the mixin below: Django's form metaclass
    only collects fields declared on the class being defined and on bases that
    already carry `declared_fields`, so a field set on a plain mixin never reaches
    form.fields and would silently not render.
    """
    return PhoneNumberField(
        region='IE',
        required=True,
        label="Phone Number",
        help_text="Irish numbers only (e.g. 085..., 01..., or +353 ...)",
    )


class IrishPhoneSignupMixin:
    """Validates the signup phone number and stores it on the user.

    Shared between the email and Google signup paths. Google signups collected no
    phone at all until this was added, so every social signup reopened the gap the
    normalise_phone_numbers backfill had just closed: a guardian on a class list
    with no way to reach them.
    """

    def clean_phone_number(self):
        number = self.cleaned_data.get('phone_number')
        if not number:
            raise ValidationError("Phone number is required.")

        # getattr, because an unparseable entry arrives as a plain string with no
        # country_code rather than raising.
        if getattr(number, 'country_code', None) != 353:
            raise ValidationError("Please enter an Irish phone number (+353 or 0...).")

        return number

    def save(self, request):
        user = super().save(request)

        phone = self.cleaned_data.get('phone_number')
        if phone:
            user.mobile_phone = phone
            user.save(update_fields=['mobile_phone'])

        return user


class CustomSignupForm(IrishPhoneSignupMixin, SignupForm):
    first_name = forms.CharField(max_length=150, required=True)
    last_name = forms.CharField(max_length=150, required=True)
    lessons = forms.BooleanField(label="I wish to sign up for swimming lessons.",
                                 required=False)
    phone_number = irish_phone_field()
    captcha = ReCaptchaField(widget=ReCaptchaV2Checkbox())

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True
        self.fields['last_name'].required = True
        self.fields['password1'].help_text = (
            "Must be 8+ characters, not too common or all numbers."
        )

    def save(self, request):
        # The mixin creates the user and stores the phone number.
        user = super().save(request)

        # Check if the 'lessons' checkbox is checked
        if self.cleaned_data.get('lessons', False):
            # Replace 'Guardian' with the name of the group you want to assign the user to
            group_name = 'Guardian'
            group, _ = Group.objects.get_or_create(name=group_name)
            user.groups.add(group)

        # Return the user instance
        return user


class CustomSocialSignupForm(IrishPhoneSignupMixin, SocialSignupForm):
    """Google signup, which allauth otherwise completes with whatever the provider
    returns — never a phone number. No captcha here: the provider has already
    established there is a person behind the request."""

    phone_number = irish_phone_field()


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
        fields = ['first_name', 'last_name', 'dob', 'sco_role_num', 'medical_info', 'notes']
        widgets = {
            'dob': forms.DateInput(attrs={'type': 'date', 'required': True}),
            'medical_info': forms.Textarea(attrs={
                'rows': 3,
                'placeholder': 'e.g. asthma, epilepsy, allergies, hearing aid. '
                               'Leave blank if there is nothing.',
            }),
            'notes': forms.Textarea(attrs={'rows': 4}),
        }
        labels = {
            'first_name': 'First Name',
            'last_name': 'Last Name',
            'dob': 'Date of Birth',
            'sco_role_num': 'School Role Number',
            'medical_info': 'Medical information',
            'notes': 'Other notes',
        }
        help_texts = {
            'medical_info': 'Shown to your child\'s teacher at poolside.',
            'notes': 'Not shown to teachers.',
        }

class GuardianOptInForm(forms.Form):
    become_guardian = forms.BooleanField(label="I would like to become a guardian", required=True)


class JoinSchoolsForm(forms.Form):
    join_schools = forms.BooleanField(
        label="I want to join the Schools Program",
        required=True
    )
