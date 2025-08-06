from django import forms
from lessons.models import Product
from .models import WaitingList

class PublicWaitingListForm(forms.ModelForm):
    is_transfer_request = forms.ChoiceField(
        choices=[(False, 'New Lesson'), (True, 'Transfer Request')],
        widget=forms.RadioSelect,
        label="Application Type"
    )
    notes = forms.CharField(
        required=False,
        widget=forms.Textarea(attrs={
            'rows': 3,
            'placeholder': 'Add any special considerations or preferences…',
            'class': 'w-full px-3 py-2 border border-gray-300 rounded-md shadow-sm focus:ring-red-500 focus:border-red-500'
        }),
        label="Notes (optional)"
    )

    class Meta:
        model = WaitingList
        fields = [
            'is_transfer_request',
            'preferred_lesson_1',
            'preferred_lesson_2',
            'preferred_lesson_3',
            'notes',
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
