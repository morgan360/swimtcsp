from decimal import Decimal
from django.conf import settings
from schools.models import ScoLessons
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
        products = ScoLessons.objects.filter(id__in=product_ids)

        cart = self.cart.copy()

        for product in products:
            product_id = str(product.id)
            # Ensure the product object is added without overwriting quantity
            if product_id in cart:
                cart[product_id]['product'] = product
                # Assume 'quantity' has been set correctly when the item was added
                cart[product_id]['price'] = Decimal(cart[product_id]['price'])
                cart[product_id]['total_price'] = cart[product_id]['price'] * cart[product_id].get('quantity', 1)
                # Directly retrieve 'swimling' assuming it's set correctly during 'add'
                yield cart[product_id]

    def __len__(self):
        """
        Count all items in the cart.
        """
        return len(self.cart)

    def add(self, product, swimling, quantity=1):
        """
        Add a product and swimling to the cart or update its quantity.
        """
        product_id = str(product.id)
        swimling_id = str(swimling.id)  # Convert swimling ID to string

        if product_id in self.cart:
            # Product exists in the cart, update the quantity
            self.cart[product_id]['quantity'] += quantity
        else:
            # Product does not exist, add it to the cart
            self.cart[product_id] = {
                'quantity': quantity,  # Initialize quantity for new items
                'price': str(product.price),
                'swimling': swimling_id,  # Store the swimling ID
            }

        # Always update price and swimling ID in case they have changed
        self.cart[product_id]['price'] = str(product.price)
        self.cart[product_id]['swimling'] = swimling_id

        self.save()

    def save(self):
        # Mark the session as "modified" to ensure it gets saved
        self.session.modified = True

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
