from .models import Cart

def cart(request):
    """Make cart available in all templates"""
    if request.user.is_authenticated:
        try:
            cart = Cart.objects.get(user=request.user)
        except Cart.DoesNotExist:
            cart = None
    else:
        cart_id = request.session.get('cart_id')
        if cart_id:
            try:
                cart = Cart.objects.get(id=cart_id)
            except Cart.DoesNotExist:
                cart = None
        else:
            cart = None
    
    return {
        'cart': cart,
        'cart_total_items': cart.total_items if cart else 0
    }