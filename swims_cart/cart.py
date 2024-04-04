from decimal import Decimal
from django.conf import settings
from swims.models import PublicSwimProduct, PriceVariant
from django.shortcuts import render
from django.shortcuts import get_object_or_404
from datetime import date, datetime

class Cart(object):
    """
            Initialize the cart.
    """
    def __init__(self, request):
        self.request = request
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def __iter__(self):
        for product_id, variations in self.cart.items():
            product_id = int(product_id)
            for variation, quantity in variations.items():
                variation = int(variation)
                yield product_id, variation, quantity

    def add(self, product_id, variation_list, quantity_list, next_occurrence_date):
        """
            Adds a product and its variations to the cart.

            Parameters:
            - product_id (str): The ID of the product to add.
            - variation_list (list): A list of variation IDs for the product.
            - quantity_list (list): A list of quantities corresponding to each variation.
            - next_occurrence_date (date): The next occurrence date for the product.

            Each product in the cart is stored with its variations, each variation's quantity,
            and the next occurrence date of the product.
            """
        product_str = str(product_id)
        next_occurrence_date_str = next_occurrence_date.strftime('%Y-%m-%d')

        # Initialize the product in the cart if not already present
        if product_str not in self.cart:
            self.cart[product_str] = {'variations': {}, 'next_occurrence_date': next_occurrence_date_str}
        else:
            # Ensure variations key exists even if the product is already in the cart
            if 'variations' not in self.cart[product_str]:
                self.cart[product_str]['variations'] = {}
            # Update the next occurrence date in case it's a repeated addition/updated info
            self.cart[product_str]['next_occurrence_date'] = next_occurrence_date_str

        # Iterate through each variation and quantity
        for variation, quantity in zip(variation_list, quantity_list):
            # Here, safely access 'variations' since it's ensured to exist above
            self.cart[product_str]['variations'][str(variation)] = quantity

        self.save()

    def remove(self, product_id):
        product_id = str(product_id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def update(self, product_id, quantity):
        product_id = str(product_id)
        if product_id in self.cart:
            self.cart[product_id]['quantity'] = quantity
            self.save()

    def clear(self):
        self.cart = {}
        del self.session[settings.CART_SESSION_ID]
        self.save()



    def cart_retrieve(self):
        """
        Retrieves the single product in the cart, along with its variations, quantities,
        and the total cost.
        """
        if not self.cart:
            return {'empty': True}

        # Assuming there is only one product in the cart.
        product_str = next(iter(self.cart))
        product_id = int(product_str)
        product = get_object_or_404(PublicSwimProduct, id=product_id)

        # Retrieve all the variations in the cart for this product.
        variation_ids = self.cart[product_str].get('variations', {})
        variation_table = []
        total = 0

        for variation_id, quantity in variation_ids.items():
            variation = get_object_or_404(PriceVariant, id=variation_id)
            price = variation.price
            sub_total = price * quantity
            total += sub_total
            variation_table.append([variation.variant, price, quantity, sub_total])

        # Assuming 'next_occurrence_date' is directly accessible in the product's cart data.
        next_occurrence_date_str = self.cart[product_str].get('next_occurrence_date', None)

        if next_occurrence_date_str is not None:
            next_occurrence_date = datetime.strptime(next_occurrence_date_str, '%Y-%m-%d').date()
        else:
            next_occurrence_date = None

        context = {
            'product': product,
            'variation_table': variation_table,
            'total': total,
            'next_occurrence_date': next_occurrence_date,
            'empty': False,
        }

        return context

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(item['total_price'] for item in self.cart.values())

    def clear_cart(self):
        self.cart = {}
        self.session[settings.CART_SESSION_ID] = {}

    def save(self):
        """
        Save the cart into the session.
        """
        self.session.modified = True