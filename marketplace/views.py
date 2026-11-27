import uuid
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from django.urls import reverse
from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.core.cache import cache
from django.db.models import Q, Sum

from .forms import (
    CustomUserCreationForm, ProductForm, OrderForm, FarmerBankForm,
)
from .models import (
    Product, Order, CustomUser, Category, Cart, CartItem,
    FarmerSubaccount, PaymentTransaction,
)
from . import paystack


# =========================================================
# HOME
# =========================================================
def home(request):
    products = Product.objects.filter(is_available=True).order_by('-created_at')[:6]
    categories = Category.objects.all()
    return render(request, 'marketplace/home.html', {
        'products': products,
        'categories': categories,
    })


# =========================================================
# AUTH
# =========================================================
def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome to E-Agro.")
            return redirect('farmer_dashboard' if user.is_farmer() else 'marketplace')
        messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    return render(request, 'registration/register.html', {'form': form})


class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True

    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().username}!")
        return super().form_valid(form)

    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password.")
        return super().form_invalid(form)

    def get_success_url(self):
        user = self.request.user
        if user.is_authenticated and user.is_farmer():
            return reverse('farmer_dashboard')
        return reverse('marketplace')


def custom_logout(request):
    logout(request)
    return redirect('login')


# =========================================================
# MARKETPLACE / PRODUCTS
# =========================================================
@login_required
def marketplace(request):
    query = request.GET.get('q', '')
    category_id = request.GET.get('category', '')

    products = Product.objects.filter(is_available=True).select_related('farmer', 'category')

    if query:
        products = products.filter(
            Q(name__icontains=query) |
            Q(description__icontains=query) |
            Q(category__name__icontains=query) |
            Q(farmer__username__icontains=query)
        )
    if category_id:
        products = products.filter(category_id=category_id)

    categories = Category.objects.all()

    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_id,
    }

    if request.headers.get('HX-Request'):
        return render(request, 'marketplace/_product_grid.html', context)
    return render(request, 'marketplace/marketplace.html', context)


@login_required
def product_detail(request, pk):
    product = get_object_or_404(
        Product.objects.select_related('farmer', 'category'), pk=pk
    )
    related = Product.objects.filter(
        farmer=product.farmer, is_available=True
    ).exclude(pk=product.pk)[:4]
    return render(request, 'marketplace/product_detail.html', {
        'product': product,
        'related_products': related,
    })


@login_required
def add_product(request):
    if not request.user.is_farmer():
        messages.warning(request, "Only farmers can add products.")
        return redirect('marketplace')

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES)
        if form.is_valid():
            product = form.save(commit=False)
            product.farmer = request.user
            product.save()
            messages.success(request, "Product added successfully!")
            return redirect('farmer_dashboard')
    else:
        form = ProductForm()
    return render(request, 'marketplace/add_product.html', {'form': form})


@login_required
def edit_product(request, pk):
    if not request.user.is_farmer():
        messages.error(request, "Only farmers can edit products.")
        return redirect('marketplace')

    product = get_object_or_404(Product, pk=pk, farmer=request.user)

    if request.method == 'POST':
        form = ProductForm(request.POST, request.FILES, instance=product)
        if form.is_valid():
            form.save()
            messages.success(request, "Product updated.")
            return redirect('farmer_dashboard')
    else:
        form = ProductForm(instance=product)
    return render(request, 'marketplace/edit_product.html', {
        'form': form, 'product': product,
    })


@login_required
def delete_product(request, pk):
    if not request.user.is_farmer():
        messages.error(request, "Only farmers can delete products.")
        return redirect('marketplace')

    product = get_object_or_404(Product, pk=pk, farmer=request.user)
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted.")
        return redirect('farmer_dashboard')
    return render(request, 'marketplace/delete_product.html', {'product': product})


# =========================================================
# CART
# =========================================================
@login_required
def add_to_cart(request, product_id):
    if not request.user.is_buyer():
        if request.headers.get('HX-Request'):
            return JsonResponse({'ok': False, 'error': 'Only buyers can add to cart'}, status=403)
        messages.error(request, "Only buyers can add items to cart.")
        return redirect('marketplace')

    product = get_object_or_404(Product, pk=product_id, is_available=True)
    cart, _ = Cart.objects.get_or_create(buyer=request.user)

    item, created = CartItem.objects.get_or_create(
        cart=cart, product=product, defaults={'quantity': 1}
    )
    if not created:
        if item.quantity < product.quantity:
            item.quantity += 1
            item.save()
        else:
            if request.headers.get('HX-Request'):
                return JsonResponse({'ok': False, 'error': 'Not enough stock'})
            messages.error(request, f"Only {product.quantity} available.")
            return redirect('view_cart')

    if request.headers.get('HX-Request'):
        return JsonResponse({'ok': True, 'cart_count': cart.items.count()})

    messages.success(request, f"Added {product.name} to your cart.")
    return redirect('view_cart')


@login_required
def view_cart(request):
    if not request.user.is_buyer():
        messages.error(request, "Only buyers can view cart.")
        return redirect('marketplace')
    cart, _ = Cart.objects.get_or_create(buyer=request.user)
    return render(request, 'marketplace/cart.html', {
        'cart': cart,
        'cart_items': cart.items.select_related('product', 'product__farmer'),
    })


@login_required
@require_POST
def update_cart_item(request, item_id):
    if not request.user.is_buyer():
        return redirect('marketplace')

    item = get_object_or_404(CartItem, pk=item_id, cart__buyer=request.user)
    action = request.POST.get('action')

    if action == 'increase':
        if item.quantity < item.product.quantity:
            item.quantity += 1
            item.save()
        else:
            messages.error(request, f"Only {item.product.quantity} available.")
    elif action == 'decrease':
        if item.quantity > 1:
            item.quantity -= 1
            item.save()
        else:
            item.delete()
    elif action == 'remove':
        item.delete()

    cart = Cart.objects.get(buyer=request.user)

    if request.headers.get('HX-Request'):
        return render(request, 'marketplace/_cart_body.html', {
            'cart': cart,
            'cart_items': cart.items.select_related('product', 'product__farmer'),
        })
    return redirect('view_cart')


# =========================================================
# ORDERS + PAYMENT
# =========================================================
@login_required
def place_order(request):
    if not request.user.is_buyer():
        messages.error(request, "Only buyers can place orders.")
        return redirect('marketplace')

    cart, _ = Cart.objects.get_or_create(buyer=request.user)
    if cart.items.count() == 0:
        messages.error(request, "Your cart is empty.")
        return redirect('marketplace')

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            payment_method = form.cleaned_data['payment_method']
            delivery_address = form.cleaned_data['delivery_address']

            if payment_method == 'PAYSTACK' and not request.user.email:
                messages.error(request, "Please add an email to your profile before paying online.")
                return redirect('view_cart')

            reference = None
            payment_status = 'PENDING'
            if payment_method == 'PAYSTACK':
                reference = f"EAGRO-{uuid.uuid4().hex[:16].upper()}"

            created_orders = []
            for item in cart.items.select_related('product'):
                order = Order.objects.create(
                    buyer=request.user,
                    product=item.product,
                    quantity=item.quantity,
                    price_at_order=item.product.price,
                    total_price=item.total_price,
                    payment_method=payment_method,
                    payment_status=payment_status,
                    payment_reference=reference or '',
                    delivery_address=delivery_address,
                    buyer_phone=request.user.phone_number,
                )
                created_orders.append(order)

                # Reserve stock
                product = item.product
                product.quantity -= item.quantity
                if product.quantity <= 0:
                    product.quantity = 0
                    product.is_available = False
                product.save()

            cart.items.all().delete()

            if payment_method == 'PAYSTACK':
                total_kobo = int(sum((o.total_price for o in created_orders), 0) * 100)

                # OPTIONAL: split with farmer subaccount if exists
                # (Only apply split when all items are from the same farmer —
                #  otherwise fall back to single-account payment.)
                farmers = {o.product.farmer_id for o in created_orders}
                subaccount_code = None
                transaction_charge = None
                if len(farmers) == 1:
                    farmer_id = next(iter(farmers))
                    sub = FarmerSubaccount.objects.filter(
                        farmer_id=farmer_id, is_verified=True
                    ).exclude(subaccount_code='').first()
                    if sub:
                        subaccount_code = sub.subaccount_code
                        commission_kobo = int(total_kobo * float(sub.percentage_charge) / 100)
                        transaction_charge = commission_kobo

                try:
                    data = paystack.initialize_transaction(
                        email=request.user.email,
                        amount_kobo=total_kobo,
                        reference=reference,
                        callback_url=settings.PAYSTACK_CALLBACK_URL,
                        subaccount=subaccount_code,
                        transaction_charge=transaction_charge,
                        metadata={
                            'buyer_id': request.user.id,
                            'order_ids': [o.id for o in created_orders],
                            'order_refs': [o.order_id for o in created_orders],
                        },
                    )
                except Exception as e:
                    messages.error(request, f"Payment setup failed: {e}")
                    return redirect('view_cart')

                PaymentTransaction.objects.create(
                    buyer=request.user,
                    reference=reference,
                    amount_kobo=total_kobo,
                    authorization_url=data['authorization_url'],
                    access_code=data['access_code'],
                    raw_response=data,
                )
                return redirect(data['authorization_url'])

            messages.success(request, "Order placed! The farmer will contact you soon.")
            return redirect('buyer_dashboard')
    else:
        form = OrderForm()

    return render(request, 'marketplace/place_order.html', {'cart': cart, 'form': form})


@login_required
def payment_callback(request):
    reference = request.GET.get('reference')
    if not reference:
        messages.error(request, "Missing payment reference.")
        return redirect('buyer_dashboard')

    try:
        data = paystack.verify_transaction(reference)
    except Exception as e:
        messages.error(request, f"Could not verify payment: {e}")
        return redirect('buyer_dashboard')

    if data.get('status') == 'success':
        _mark_orders_paid(reference, data)
        return render(request, 'marketplace/payment_success.html', {
            'reference': reference,
            'amount_naira': data.get('amount', 0) / 100,
        })
    return render(request, 'marketplace/payment_failure.html', {
        'reference': reference,
    })


@csrf_exempt
@require_POST
def payment_webhook(request):
    signature = request.headers.get('x-paystack-signature', '')
    if not paystack.verify_webhook_signature(request.body, signature):
        return HttpResponse(status=401)

    try:
        event = json.loads(request.body)
    except json.JSONDecodeError:
        return HttpResponse(status=400)

    if event.get('event') == 'charge.success':
        data = event.get('data', {})
        reference = data.get('reference')
        if reference:
            _mark_orders_paid(reference, data)

    return HttpResponse(status=200)


def _mark_orders_paid(reference, data):
    """Idempotent: mark every Order with this reference as PAID."""
    txn = PaymentTransaction.objects.filter(reference=reference).first()
    if txn and txn.status == 'success':
        return  # already processed

    if not txn:
        metadata = data.get('metadata') or {}
        txn = PaymentTransaction.objects.create(
            buyer_id=metadata.get('buyer_id') or 1,
            reference=reference,
            amount_kobo=data.get('amount', 0),
        )

    txn.status = 'success'
    txn.paid_at = timezone.now()
    txn.raw_response = data
    txn.save(update_fields=['status', 'paid_at', 'raw_response'])

    Order.objects.filter(payment_reference=reference).update(
        payment_status='PAID',
        paid_at=timezone.now(),
        status='CONFIRMED',
    )


# =========================================================
# FARMER BANK DETAILS (Paystack Subaccount)
# =========================================================
@login_required
def farmer_bank_details(request):
    if not request.user.is_farmer():
        messages.error(request, "Only farmers can access this page.")
        return redirect('marketplace')

    # Cache the bank list for 24h
    banks = cache.get('paystack_banks')
    if not banks:
        banks = paystack.list_banks()
        cache.set('paystack_banks', banks, 60 * 60 * 24)

    bank_choices = [(b['code'], b['name']) for b in banks] if banks else []
    sub = FarmerSubaccount.objects.filter(farmer=request.user).first()

    if request.method == 'POST':
        form = FarmerBankForm(request.POST, instance=sub, bank_choices=bank_choices)
        if form.is_valid():
            instance = form.save(commit=False)
            instance.farmer = request.user
            instance.settlement_bank = form.cleaned_data['bank_code']
            instance.percentage_charge = settings.PLATFORM_COMMISSION_PERCENT
            try:
                data = paystack.create_subaccount(
                    business_name=instance.business_name,
                    settlement_bank=instance.settlement_bank,
                    account_number=instance.account_number,
                    percentage_charge=float(instance.percentage_charge),
                )
                instance.subaccount_code = data['subaccount_code']
                instance.is_verified = True
                instance.save()
                messages.success(request, "Bank details saved. You can now receive payments!")
                return redirect('farmer_dashboard')
            except Exception as e:
                messages.error(request, f"Paystack error: {e}")
    else:
        form = FarmerBankForm(instance=sub, bank_choices=bank_choices)

    return render(request, 'marketplace/farmer_bank_details.html', {
        'form': form, 'subaccount': sub,
    })


# =========================================================
# DASHBOARDS
# =========================================================
@login_required
def farmer_dashboard(request):
    if not request.user.is_farmer():
        messages.error(request, "Only farmers can access this page.")
        return redirect('marketplace')

    products = Product.objects.filter(farmer=request.user)
    orders = Order.objects.filter(product__farmer=request.user).select_related('buyer', 'product')

    pending = orders.filter(status='PENDING').count()
    confirmed = orders.filter(status='CONFIRMED').count()
    delivered = orders.filter(status='DELIVERED').count()

    subaccount = FarmerSubaccount.objects.filter(farmer=request.user, is_verified=True).first()

    context = {
        'products': products,
        'orders': orders,
        'pending_orders': pending,
        'confirmed_orders': confirmed,
        'delivered_orders': delivered,
        'subaccount': subaccount,
    }

    if request.GET.get('partial') == 'orders':
        return render(request, 'marketplace/_farmer_orders_table.html', context)
    return render(request, 'marketplace/farmer_dashboard.html', context)


@login_required
@require_POST
def update_order_status(request, order_id):
    if not request.user.is_farmer():
        messages.error(request, "Only farmers can update order status.")
        return redirect('marketplace')

    order = get_object_or_404(Order, id=order_id, product__farmer=request.user)
    new_status = request.POST.get('status')
    if new_status in dict(Order.STATUS_CHOICES):
        order.status = new_status
        order.save(update_fields=['status', 'updated_at'])
        messages.success(request, f"Order #{order.order_id} → {order.get_status_display()}.")
    return redirect('farmer_dashboard')


@login_required
def buyer_dashboard(request):
    if not request.user.is_buyer():
        messages.error(request, "Only buyers can access this page.")
        return redirect('marketplace')

    orders = Order.objects.filter(buyer=request.user).select_related('product', 'product__farmer')
    total_spent = orders.aggregate(total=Sum('total_price'))['total'] or 0
    delivered_orders = orders.filter(status='DELIVERED').count()

    favorite_farmers = CustomUser.objects.filter(
        products__orders__buyer=request.user, user_type='FARMER'
    ).distinct()

    return render(request, 'marketplace/buyer_dashboard.html', {
        'orders': orders,
        'total_spent': total_spent,
        'delivered_orders': delivered_orders,
        'favorite_farmers': favorite_farmers,
    })