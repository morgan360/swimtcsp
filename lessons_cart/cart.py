from decimal import Decimal
from django.conf import settings
from lessons.models import Product
from users.models import Swimling


class Cart:
    def __init__(self, request):
        """
        Initialize the cart.
        """
        self.session = request.session
        cart = self.session.get(settings.CART_SESSION_ID)
        if not cart:
            # save an empty cart in the session
            cart = self.session[settings.CART_SESSION_ID] = {}
        self.cart = cart

    def __iter__(self):
        """
        Iterate over the items in the cart and get the products
        from the database.
        """
        product_ids = self.cart.keys()
        # get the product objects (details from DB) and add them to the cart.
        # Only for IDs retrieved from session data(cart)
        products = Product.objects.filter(id__in=product_ids)
        # Make a copy of the cart
        cart = self.cart.copy()
        # loop through the product info retrieved from DB
        for product in products:
            cart[str(product.id)]['product'] = product
            cart[str(product.id)]['quantity'] = 1
        # retrieve product_id
        for item in cart.values():
            # product_id = item.get('product_id')  # Retrieve the product ID
            # if product_id:
            #     product = Product.objects.get(id=product_id)
            # item['product'] = product
            item['price'] = Decimal(item['price'])
            item['total_price'] = item['price'] * item['quantity']
            item['swimling'] = item['swimling']
            yield item

    def __len__(self):
        """
        Count all items in the cart.
        """
        return len(self.cart)

    def add(self, product, swimling, quantity=1):
        """
        Add a product and swimling to the cart or update the quantity.
        """
        product_id = str(product.id)
        swimling_id = str(swimling.id)

        # Check if the product already exists in the cart
        if product_id in self.cart:
            # If the product is already in the cart, safely increment the quantity
            self.cart[product_id].setdefault('quantity', 0)
            self.cart[product_id]['quantity'] += quantity
        else:
            # If the product is not in the cart, initialize it with the given quantity and details
            self.cart[product_id] = {
                'quantity': quantity,
                'price': str(product.price),  # Store price as a string to avoid serialization issues
                'swimling': swimling_id,  # Store the swimling ID associated with this product
            }

        # Save the cart changes to the session
        self.save()

    def remove(self, product):
        """
        Remove a product from the cart.
        """
        product_id = str(product.id)
        if product_id in self.cart:
            del self.cart[product_id]
            self.save()

    def clear(self):
        # remove cart from session
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def get_total_price(self):
        return sum(Decimal(item['price']) for item in self.cart.values())
