from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.http import JsonResponse
from django.contrib.auth.decorators import login_required
from .models import Cart, CartItem
from store.models import Product

def _get_cart(request):
    """Helper function to get or create cart"""
    if request.user.is_authenticated:
        cart, created = Cart.objects.get_or_create(user=request.user)
    else:
        cart_id = request.session.get('cart_id')
        if cart_id:
            cart = get_object_or_404(Cart, id=cart_id)
        else:
            cart = Cart.objects.create()
            request.session['cart_id'] = cart.id
    return cart

def cart_detail(request):
    cart = _get_cart(request)
    return render(request, 'cart/detail.html', {'cart': cart})

@require_POST
def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = _get_cart(request)
    
    # Check if item already in cart
    cart_item, created = CartItem.objects.get_or_create(
        cart=cart,
        product=product,
        defaults={'quantity': 1}
    )
    
    if not created:
        cart_item.quantity += 1
        cart_item.save()
    
    messages.success(request, f'"{product.title}" added to cart!')
    
    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return JsonResponse({
            'success': True,
            'cart_total_items': cart.total_items,
            'message': f'"{product.title}" added to cart!'
        })
    
    return redirect('cart:cart_detail')

@require_POST
def cart_remove(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = _get_cart(request)
    
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        cart_item.delete()
        messages.success(request, f'"{product.title}" removed from cart!')
    except CartItem.DoesNotExist:
        messages.error(request, 'Item not found in cart!')
    
    return redirect('cart:cart_detail')

@require_POST
def cart_update(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    cart = _get_cart(request)
    quantity = int(request.POST.get('quantity', 1))
    
    try:
        cart_item = CartItem.objects.get(cart=cart, product=product)
        if quantity > 0:
            cart_item.quantity = quantity
            cart_item.save()
            messages.success(request, 'Cart updated!')
        else:
            cart_item.delete()
            messages.success(request, 'Item removed from cart!')
    except CartItem.DoesNotExist:
        messages.error(request, 'Item not found in cart!')
    
    return redirect('cart:cart_detail')

# NEW FUNCTION ADDED FOR CHECKOUT AUTHENTICATION
def proceed_to_checkout(request):
    """Check if user is authenticated, if not redirect to login"""
    cart = _get_cart(request)
    
    # Check if cart is empty
    if not cart.items.exists():
        messages.error(request, "Your cart is empty!")
        return redirect('cart:cart_detail')
    
    if not request.user.is_authenticated:
        messages.info(request, "Please login to proceed to checkout")
        # Store the current URL to redirect back after login
        request.session['next_url'] = 'cart:proceed_checkout'
        return redirect('accounts:login')
    
    # If user is authenticated, transfer session cart to user cart if needed
    if not cart.user and request.user.is_authenticated:
        # User was anonymous but now logged in - transfer cart
        user_cart, created = Cart.objects.get_or_create(user=request.user)
        
        # Transfer all items from session cart to user cart
        for item in cart.items.all():
            user_cart_item, item_created = CartItem.objects.get_or_create(
                cart=user_cart,
                product=item.product,
                defaults={'quantity': item.quantity}
            )
            if not item_created:
                user_cart_item.quantity += item.quantity
                user_cart_item.save()
        
        # Delete the anonymous cart
        cart.delete()
        # Update session to use user's cart
        request.session['cart_id'] = user_cart.id
        cart = user_cart
    
    # Proceed to checkout
    return redirect('orders:checkout')

# NEW FUNCTION ADDED FOR CART TRANSFER AFTER LOGIN
def transfer_session_cart_to_user(request, user):
    """Transfer session cart to user cart after login"""
    cart_id = request.session.get('cart_id')
    if cart_id:
        try:
            session_cart = Cart.objects.get(id=cart_id)
            if not session_cart.user:  # It's an anonymous cart
                user_cart, created = Cart.objects.get_or_create(user=user)
                
                # Transfer items
                for item in session_cart.items.all():
                    user_cart_item, item_created = CartItem.objects.get_or_create(
                        cart=user_cart,
                        product=item.product,
                        defaults={'quantity': item.quantity}
                    )
                    if not item_created:
                        user_cart_item.quantity += item.quantity
                        user_cart_item.save()
                
                # Delete the anonymous cart
                session_cart.delete()
                # Update session
                request.session['cart_id'] = user_cart.id
                return True
        except Cart.DoesNotExist:
            pass
    return False