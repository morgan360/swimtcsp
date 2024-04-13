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
        Iterate over the items in the cart and get the products from the database.
        """
        product_ids = self.cart.keys()
        products = Product.objects.filter(id__in=product_ids)
        products_dict = {str(product.id): product for product in products}

        for item_id, item in self.cart.items():
            product = products_dict.get(item_id)
            if product:
                yield {
                    'product_id': item_id,
                    'product': product,
                    'quantity': item.get('quantity', 1),  # Default to 1 if quantity is missing
                    'price': Decimal(item['price']),
                    'total_price': Decimal(item['price']) * item.get('quantity', 1),
                    # Calculate using a default quantity of 1
                    'swimling': item['swimling'],
                }

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

        if product_id in self.cart:
            # If the product is already in the cart, increment the quantity
            self.cart[product_id]['quantity'] = self.cart[product_id].get('quantity', 0) + quantity
        else:
            # If the product is not in the cart, create a new entry with all details
            self.cart[product_id] = {
                'quantity': quantity,
                'price': str(product.price),
                'swimling': swimling_id,
            }

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

    def save(self):
        """
        Mark the session as 'modified' to make sure it gets saved by Django.
        """
        self.session.modified = True