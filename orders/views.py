import stripe
import paypalrestsdk
from django.conf import settings
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.urls import reverse
from django.http import JsonResponse
from .models import Order, OrderItem
from cart.models import Cart
import random
import string

# Configure Stripe
stripe.api_key = settings.STRIPE_SECRET_KEY

# Configure PayPal
paypalrestsdk.configure({
    "mode": settings.PAYPAL_MODE,
    "client_id": settings.PAYPAL_CLIENT_ID,
    "client_secret": settings.PAYPAL_CLIENT_SECRET
})

@login_required
def checkout(request):
    cart = get_object_or_404(Cart, user=request.user)
    
    if not cart.items.exists():
        messages.error(request, "Your cart is empty!")
        return redirect('cart:cart_detail')
    
    if request.method == 'POST':
        # Process order
        order_number = ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        
        order = Order.objects.create(
            user=request.user,
            order_number=order_number,
            payment_method=request.POST.get('payment_method'),
            total_amount=cart.total_price,
            full_name=request.POST.get('full_name'),
            email=request.POST.get('email'),
            phone=request.POST.get('phone'),
            address=request.POST.get('address'),
            city=request.POST.get('city'),
            state=request.POST.get('state'),
            postal_code=request.POST.get('postal_code'),
            country=request.POST.get('country'),
        )
        
        # Create order items
        for cart_item in cart.items.all():
            OrderItem.objects.create(
                order=order,
                product=cart_item.product,
                quantity=cart_item.quantity,
                price=cart_item.product.price
            )
        
        # Clear cart
        cart.items.all().delete()
        
        # Redirect to payment based on method
        if order.payment_method == 'stripe':
            return redirect('orders:stripe_payment', order_id=order.id)
        elif order.payment_method == 'paypal':
            return redirect('orders:paypal_payment', order_id=order.id)
    
    return render(request, 'orders/checkout.html', {'cart': cart})

@login_required
def stripe_payment(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        try:
            # Create Stripe Checkout Session (Recommended approach)
            checkout_session = stripe.checkout.Session.create(
                payment_method_types=['card'],
                line_items=[{
                    'price_data': {
                        'currency': 'usd',
                        'product_data': {
                            'name': f'Order #{order.order_number}',
                            'description': f'MangaShop Purchase',
                        },
                        'unit_amount': int(order.total_amount * 100),  # cents
                    },
                    'quantity': 1,
                }],
                mode='payment',
                success_url=request.build_absolute_uri(
                    reverse('orders:payment_success', kwargs={'order_id': order.id})
                ),
                cancel_url=request.build_absolute_uri(
                    reverse('orders:payment_cancel', kwargs={'order_id': order.id})
                ),
                metadata={
                    'order_id': order.id
                }
            )
            
            return redirect(checkout_session.url)
            
        except Exception as e:
            messages.error(request, f"Payment error: {str(e)}")
            return redirect('orders:checkout')
    
    # For GET request, show Stripe payment form
    return render(request, 'orders/stripe_payment.html', {
        'order': order,
        'stripe_publishable_key': settings.STRIPE_PUBLISHABLE_KEY,
    })

@login_required
def paypal_payment(request, order_id):
    """Show PayPal payment page first, then process payment on POST"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    if request.method == 'POST':
        # Process PayPal payment (your existing logic)
        try:
            payment = paypalrestsdk.Payment({
                "intent": "sale",
                "payer": {
                    "payment_method": "paypal"
                },
                "redirect_urls": {
                    "return_url": request.build_absolute_uri(
                        reverse('orders:paypal_execute', kwargs={'order_id': order.id})
                    ),
                    "cancel_url": request.build_absolute_uri(
                        reverse('orders:paypal_cancel', kwargs={'order_id': order.id})
                    )
                },
                "transactions": [{
                    "amount": {
                        "total": str(order.total_amount),
                        "currency": "USD"
                    },
                    "description": f"MangaShop Order #{order.order_number}",
                    "custom": str(order.id),
                    "invoice_number": order.order_number
                }]
            })

            if payment.create():
                for link in payment.links:
                    if link.rel == "approval_url":
                        approval_url = str(link.href)
                        return redirect(approval_url)
            else:
                messages.error(request, f"PayPal error: {payment.error}")
                return redirect('orders:paypal_payment', order_id=order.id)
                
        except Exception as e:
            messages.error(request, f"Payment error: {str(e)}")
            return redirect('orders:paypal_payment', order_id=order.id)
    
    # For GET request, show PayPal payment page (like Stripe does)
    return render(request, 'orders/paypal_payment.html', {
        'order': order,
    })

@login_required
def paypal_execute(request, order_id):
    """Execute PayPal payment after user approval"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    
    payment_id = request.GET.get('paymentId')
    payer_id = request.GET.get('PayerID')
    
    if not payment_id or not payer_id:
        messages.error(request, "Payment failed: Missing payment information")
        return redirect('orders:checkout')
    
    try:
        payment = paypalrestsdk.Payment.find(payment_id)
        
        if payment.execute({"payer_id": payer_id}):
            # Payment successful
            order.paid = True
            order.status = 'completed'
            order.payment_id = payment_id
            order.save()
            
            messages.success(request, f"Order {order.order_number} completed successfully!")
            return redirect('orders:payment_success', order_id=order.id)
        else:
            messages.error(request, f"Payment failed: {payment.error}")
            return redirect('orders:checkout')
            
    except Exception as e:
        messages.error(request, f"Payment error: {str(e)}")
        return redirect('orders:checkout')

@login_required
def paypal_cancel(request, order_id):
    """Handle cancelled PayPal payment"""
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'cancelled'
    order.save()
    
    messages.warning(request, "PayPal payment was cancelled.")
    return redirect('cart:cart_detail')

@login_required
def payment_success(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'orders/payment_success.html', {'order': order})

@login_required
def payment_cancel(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order.status = 'cancelled'
    order.save()
    
    messages.warning(request, "Payment was cancelled.")
    return redirect('cart:cart_detail')