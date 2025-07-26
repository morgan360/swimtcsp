from django import forms

class CouponApplyForm(forms.Form):
    code = forms.CharField(
        max_length=20,
        required=False,
        label="Coupon Code",
        widget=forms.TextInput(attrs={
            'placeholder': 'Enter coupon code (optional)',
            'class': 'form-input border border-gray-300 px-3 py-2 rounded w-full'
        })
    )

