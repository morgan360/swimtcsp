from django.urls import reverse
from django.shortcuts import render, redirect
from .models import Order, OrderItem
# from swims.models import PublicSwimProduct, PriceVariant
from lessons.models import Product
# from .forms import OrderCreateForm
# from .tasks import order_created
from lessons_cart.cart import Cart as ClassCart
# from .tasks import order_created  # Import the task function if it's defined in a separate module
from django.contrib.auth.decorators import login_required


@login_required
def order_create(request):
    order_type = request.GET['value']

    # If SWIM or Class
    if order_type == 'public_class':
        cart = ClassCart(request)
        order = Order.objects.create(user=request.user)

        for item in cart:
            OrderItem.objects.create(order=order,
                                     product=item['product'],
                                     price=item['price'],
                                     quantity=item['quantity'])

        # Clear the cart
        cart.clear()
        order_created(order.id)
        # Set the order in the session
        request.session['order_id'] = order.id
        # return render(request, 'orders/order/created.html',{'order': order})
        # redirect for payment
        return redirect(reverse('lessons_payment:process'))

        current_user = request.user
        # Retrieve the order items for the created order
        order_items = OrderItem.objects.filter(order=order)
        return render(request,
                      'orders/order/created.html',
                      {'order': order,
                       'order_type': order_type,
                       'order_items': order_items,
                       # Pass the order_items to the template
                       'current_user': current_user})


def order_created(order_id):
    # Retrieve the order object based on the provided order_id
    order = Order.objects.get(id=order_id)

    # Perform any additional actions or processing for the order creation
    # For example, you can send email notifications, update inventory, etc.

    # Return a success message or any relevant data
    return f"Order {order_id} created successfully!"


# Public Swim  Order Create
def swim_order_create(request):
    cart = SwimCart(request)
    if request.method == 'POST':
        form = OrderCreateForm(request.POST)
        if form.is_valid():
            order = form.save()
            for item in cart:
                OrderItem.objects.create(order=order,
                                         product=item['product'],
                                         price=item['price'],
                                         quantity=item['quantity'])

            # clear the cart
            cart.clear()
            # Call the order_created function directly
            order_created(order.id)
            return render(request,
                          'orders/order/created.html',
                          {'order': order})
    else:
        form = OrderCreateForm()
    return render(request,
                  'orders/order/create.html',
                  {'cart': cart, 'form': form})
