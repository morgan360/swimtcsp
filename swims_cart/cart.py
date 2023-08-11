from decimal import Decimal
from django.conf import settings
from swims.models import PublicSwimProduct, PriceVariant
from django.shortcuts import render


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

    def add(self, product_id, variation_list, quantity_list):
        product = str(product_id)
        # Iterate through each variant
        i = 0
        self.cart[product] = {}
        for variation in variation_list:
            self.cart[product][variation] = quantity_list[i]
            i += 1
        self.save()

    def save(self):
        # mark the session as "modified" to make sure it gets saved
        self.session.modified = True

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

    def cart_retrieve(self, request=None):
        """
            Iterate over the items in the cart and get the products
            """
        self.request = request
        if len(self.cart)==0:
            context = {
                'empty': True,
            }
        else:
            product_str = next(iter(self.cart))
            product_id = int(product_str)

            product = PublicSwimProduct.objects.get(id=product_id)
            # retrieve all the variatiions in cart
            variation_ids = list(self.cart[product_str].keys())
            variation_table = []
            total = 0
            for variation_str in variation_ids:
                variation_id = int(variation_str)
                variant = PriceVariant.objects.get(id=variation_id)
                variant_name = variant.variant
                price = variant.price
                quantity = self.cart[product_str][variation_str]
                sub_total = price * quantity
                total += sub_total
                table = [variant_name, price, quantity, sub_total]
                variation_table.append(table)
            context = {'product': product, 'variation_table': variation_table, 'total': total}
        return context

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    def get_total_price(self):
        return sum(item['total_price'] for item in self.cart.values())

    def clear_cart(self):
        self.cart = {}
        self.session[settings.CART_SESSION_ID] = {}
