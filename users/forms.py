from django import forms
from allauth.account.forms import SignupForm
from django.contrib.auth.models import Group


class CustomSignupForm(SignupForm):
    first_name = forms.CharField(max_length=150, required=True)
    lessons = forms.BooleanField(label="I wish to apply for children's lessons",
                                 required=False)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['first_name'].required = True

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
