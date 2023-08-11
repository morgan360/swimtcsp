from django import forms
from .cart import Cart

class CartAddProductForm(forms.Form):
    quantity = forms.IntegerField(
        widget=forms.TextInput(attrs={
            'type': 'number',
            'value': '1',
            'min': '1',
            'max': '10',
            'step': '1',
            'class': 'form-control input-number'
        })
    )
    override = forms.BooleanField(required=False,
        initial=False,
        widget=forms.HiddenInput)

    def __init__(self, *args, **kwargs):
        initial = kwargs.get('initial', {})
        self.product_id = initial.get('product_id')
        self.request = initial.get('request')
        self.cart = Cart(self.request) if self.request else None
        super().__init__(*args, **kwargs)

        if self.cart and 'product' in self.cart.cart.get(str(self.product_id), {}):
            self.fields['override'].widget.attrs['value'] = True
        else:
            self.fields['override'].widget.attrs['value'] = False
