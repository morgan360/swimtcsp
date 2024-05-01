from decimal import Decimal
from django.conf import settings
from lessons.models import Product
from schools.models import ScoLessons
from users.models import Swimling


class Cart:
    allowed_types = ['lesson', 'school']  # Define allowed types as a class attribute

    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(settings.CART_SESSION_ID, {})
        self.type = self.session.get(f"{settings.CART_SESSION_ID}_type", None)

    def add(self, product, type, swimling_id, quantity=1):
        """
        Add a product to the cart or update its quantity.
        If the product type differs from the cart type, clear the cart first.
        """

        # Validate product type first
        if type not in self.allowed_types:
            raise ValueError(f"Invalid product type '{type}'. Allowed types are {self.allowed_types}.")

        # Check if the cart has items and if the type matches
        if self.cart and (self.type != type):
            self.clear()  # Clear the cart if types do not match

        # After clearing, update the cart type
        self.type = type

        product_id = str(product.id)
        cart_key = f"{type}_{product_id}_{swimling_id}"

        # Add or update the cart item
        self.cart[cart_key] = {
            'quantity': quantity,
            'price': str(product.price),
            'product_id': product_id,
            'swimling_id': swimling_id,
            'type': type
        }
        self.save()

    def remove(self, cart_key):
        """
        Remove a product from the cart.
        """
        if cart_key in self.cart:
            del self.cart[cart_key]
            if not self.cart:
                self.type = None  # Reset type if cart is empty
            self.save()
        else:
            raise KeyError("Item not found in cart.")

    def clear(self):
        """
        Clear the cart.
        """
        self.cart = {}
        self.type = None
        self.save()

    def get_total_price(self):
        """
        Calculate the total price of all items in the cart.
        """
        return sum(Decimal(item['price']) * item['quantity'] for item in self.cart.values())

    def __iter__(self):
        """
        Iterate over the items in the cart and retrieve them from the database.
        """
        if self.type == 'lesson':
            product_model = Product
        else:
            product_model = ScoLessons

        product_ids = [item['product_id'] for item in self.cart.values()]
        products = product_model.objects.filter(id__in=product_ids)
        product_dict = {str(product.id): product for product in products}

        for item in self.cart.values():
            product = product_dict.get(str(item['product_id']))
            if product:
                yield {
                    'product_id': item['product_id'],
                    'product': product,
                    'quantity': item['quantity'],
                    'price': Decimal(item['price']),
                    'total_price': Decimal(item['price']) * item['quantity'],
                    'swimling': Swimling.objects.get(id=item['swimling_id']),
                    'type': item['type']
                }

    def __len__(self):
        """
        Count the number of items in the cart.
        """
        return sum(item['quantity'] for item in self.cart.values())

    def save(self):
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session[f"{settings.CART_SESSION_ID}_type"] = self.type
        self.session.modified = True  