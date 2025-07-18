from django import forms
from .models import Order

class OrderCreateForm(forms.ModelForm):
    coupon_code = forms.CharField(
        max_length=20,
        required=False,
        label='Coupon Code',
        widget=forms.TextInput(attrs={'placeholder': 'Enter coupon code'})
    )

    class Meta:
        model = Order
        fields = ['first_name', 'last_name', 'email', 'address',
                  'postal_code', 'city']

