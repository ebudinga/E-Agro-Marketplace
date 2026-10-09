from .models import Cart


def cart_count(request):
    if request.user.is_authenticated and request.user.is_buyer():
        cart = Cart.objects.filter(buyer=request.user).first()
        return {'cart_count': cart.items.count() if cart else 0}
    return {'cart_count': 0}