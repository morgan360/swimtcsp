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
        Enhances performance by reducing the number of database queries.
        """
        product_ids = list(self.cart.keys())  # Gather all product IDs from the cart
        products = Product.objects.filter(id__in=product_ids)
        products_dict = {str(product.id): product for product in products}

        for item_id, item in self.cart.items():
            product = products_dict.get(item_id)
            if product:
                yield {
                    'product_id': item_id,
                    'product': product,
                    'quantity': item['quantity'],
                    'price': Decimal(item['price']),
                    'total_price': Decimal(item['price']) * item['quantity'],
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
        This method sets the quantity to 1 if the product is added for the first time,
        or increments the quantity by 1 each time the same product is added again.
        """
        product_id = str(product.id)
        swimling_id = str(swimling.id)

        if product_id in self.cart:
            # If the product is already in the cart, increment the quantity
            if 'quantity' in self.cart[product_id]:
                self.cart[product_id]['quantity'] += quantity
            else:
                self.cart[product_id]['quantity'] = quantity
        else:
            # If the product is not in the cart, create a new entry with quantity set to 1
            self.cart[product_id] = {
                'quantity': quantity,
                'price': str(product.price),
                'swimling': swimling_id,
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

    def save(self):
        """
        Mark the session as 'modified' to make sure it gets saved by Django.
        """
        self.session.modified = True