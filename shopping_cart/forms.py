from django import forms
from users.models import Swimling
from schools.models import ScoLessons, ScoSchool


class CartAddProductForm(forms.Form):
    swimling = forms.ModelChoiceField(
        queryset=Swimling.objects.none(),
        label="Select a swimling",
    )

    def __init__(self, user, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # print("User:", user)
        queryset = Swimling.objects.filter(guardian=user)
        # print("Queryset:", queryset)
        self.fields['swimling'].queryset = queryset


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


class DirectOrderForm(forms.Form):
    lesson = forms.ModelChoiceField(
        queryset=None,
        label="Select Course",
        widget=forms.Select(attrs={
            'class': 'form-control bg-white text-gray-800 border border-gray-300 rounded shadow-sm hover:border-gray-500 focus:outline-none focus:ring focus:border-blue-300'
        }),
        empty_label="Select a course"
    )

    def __init__(self, *args, **kwargs):
        school_id = kwargs.pop('school_id', None)
        super().__init__(*args, **kwargs)
        self.fields['lesson'].queryset = ScoLessons.objects.filter(school_id=school_id)
        self.fields['lesson'].label_from_instance = self.label_from_instance

    def label_from_instance(self, obj):
        return f"{obj.name} - €{obj.price}"
