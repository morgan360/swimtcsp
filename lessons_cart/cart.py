from decimal import Decimal
from django.conf import settings
from lessons.models import Product
from users.models import Swimling


class Cart:
    def __init__(self, request):
        self.session = request.session
        self.cart = self.session.get(settings.CART_SESSION_ID, {})

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
                    'quantity': item.get('quantity', 1),  # Ensure quantity is always set
                    'price': Decimal(item['price']),
                    'total_price': Decimal(item['price']) * item.get('quantity', 1),
                    'swimling': item['swimling'],
                }


    def add(self, product, swimling_id, quantity=1):
        """
        Add a product to the cart or update its quantity.
        """
        product_id = str(product.id)  # Ensure the product ID is a string for consistent key usage
        cart_key = f"{product_id}_{swimling_id}"  # Create a unique key for the product and swimling combination

        if cart_key in self.cart:
            # Product already in the cart, increment quantity
            self.cart[cart_key]['quantity'] += quantity
        else:
            # Product not in the cart, add it
            self.cart[cart_key] = {
                'quantity': quantity,
                'price': str(product.price),  # Store price as a string for potential serialization issues
                'swimling_id': swimling_id,  # Store the swimling ID
            }

        self.save()  # Make sure to save the cart changes to the session

    def save(self):
        # Save the cart to the session
        self.session[settings.CART_SESSION_ID] = self.cart
        self.session.modified = True  # Notify Django that the session has changed

    def remove(self, cart_key):
        """
        Remove an item from the cart using the combined cart_key.
        """
        if cart_key in self.cart:
            del self.cart[cart_key]
            self.save()  # Make sure to save the cart changes to the session
        else:
            raise KeyError("Item not found in cart.")

    def clear(self):
        # remove cart from session
        del self.session[settings.CART_SESSION_ID]
        self.save()

    def get_total_price(self):
        return sum(Decimal(item['price']) for item in self.cart.values())

    # def save(self):
    #     # update the session with new cart data
    #     self.session[settings.CART_SESSION_ID] = self.cart
    #     # mark the session as "modified" to make sure it gets saved
    #     self.session.modified = True

    def __len__(self):
        """
        Count all items in the cart.
        """
        return len(self.cart)