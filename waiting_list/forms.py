from django import forms
from lessons.models import Product
from .models import WaitingList

class PublicWaitingListForm(forms.ModelForm):
    is_transfer_request = forms.ChoiceField(
        choices=[(False, 'New Lesson'), (True, 'Transfer Request')],
        widget=forms.RadioSelect,
        label="Application Type"
    )

    class Meta:
        model = WaitingList
        fields = [
            'is_transfer_request',
            'preferred_lesson_1',
            'preferred_lesson_2',
            'preferred_lesson_3',
        ]

    def __init__(self, *args, **kwargs):
        self.swimling = kwargs.pop('swimling', None)
        super().__init__(*args, **kwargs)

        if self.swimling:
            # Ensure no duplicate waiting list entry
            self.fields['preferred_lesson_1'].queryset = Product.objects.all()
            self.fields['preferred_lesson_2'].queryset = Product.objects.all()
            self.fields['preferred_lesson_3'].queryset = Product.objects.all()

    def save(self, commit=True):
        instance = super().save(commit=False)
        instance.swimling = self.swimling
        instance.product = self.cleaned_data['preferred_lesson_1']  # for uniqueness
        if commit:
            instance.save()
        return instance
