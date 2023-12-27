from django.contrib.auth import get_user_model
from import_export import resources, fields
from import_export.widgets import ForeignKeyWidget
from .models import OrderItem, Order
from swims.models import PublicSwimProduct, PriceVariant
from decimal import Decimal

# Use Django's function to get the custom user model because we have defined our own
UserModel = get_user_model()


class OrderResource(resources.ModelResource):
    user = fields.Field(
        column_name='user_id',
        attribute='user',
        widget=ForeignKeyWidget(UserModel, 'id')
    )
    product = fields.Field(
        column_name='product_id',
        attribute='product',
        widget=ForeignKeyWidget(PublicSwimProduct, 'id')  # Replace 'Product' with your actual Product model
    )

    class Meta:
        model = Order
        import_id_fields = ('id',)
        fields = ('id', 'user', 'product', 'booking', 'stripe_id',)

        # If your CSV doesn't include the Order ID, you can remove 'id' from both


class OrderItemResource(resources.ModelResource):
    order = fields.Field(
        attribute='order',
    )
    quantity = fields.Field(attribute='quantity')

    def before_import_row(self, row, **kwargs):
        order_id = row.get('id')
        variant_text = row.get('variant')

        try:
            # Retrieve the order object
            order = Order.objects.get(id=order_id)

            # Assign the order instance instead of ID
            row['order'] = order

            # Find the PriceVariant that matches the variant text and product_id
            variant = PriceVariant.objects.get(variant=variant_text, product_id=order.product_id)

            # Set the variant ID in the row for further processing
            row['variant'] = variant.id

        except Order.DoesNotExist:
            print(f"Order with ID {order_id} does not exist.")
        except PriceVariant.DoesNotExist:
            print(f"PriceVariant with variant '{variant_text}' and product_id {order.product_id} does not exist.")

    class Meta:
        model = OrderItem
        fields = ('order', 'quantity', 'variant',)  # Include 'variant' to resolve KeyError
        import_id_fields = ('order', 'variant',)
        skip_unchanged = True
        report_skipped = True
