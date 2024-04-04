from django import forms

class ParticipantQuantityForm(forms.Form):
    adult_quantity = forms.IntegerField(min_value=0, initial=0, label='Adults')
    child_quantity = forms.IntegerField(min_value=0, initial=0, label='Children')
    # Add more fields as necessary for different participant types