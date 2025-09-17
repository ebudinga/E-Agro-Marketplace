from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.contrib.auth.views import LoginView
from .forms import CustomUserCreationForm, ProductForm, OrderForm
from django.db.models import Q
from .models import Product, Order, CustomUser, Category, Cart, CartItem

def home(request):
    # Get featured products for the homepage
    products = Product.objects.filter(is_available=True).order_by('-created_at')[:6]
    
    # Get categories for navigation
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
    }
    return render(request, 'home.html', context)

def register(request):
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            try:
                user = form.save(commit=False)
                user.email = form.cleaned_data['email']
                user.phone_number = form.cleaned_data['phone_number']
                user.location = form.cleaned_data['location']
                user.user_type = form.cleaned_data['user_type']
                user.save()
                
                # Log the user in after registration
                login(request, user)
                messages.success(request, "Registration successful! Welcome to E-Agro Marketplace.")
                
                # Redirect based on user type
                if user.is_farmer():
                    return redirect('farmer_dashboard')
                else:
                    return redirect('marketplace')
                    
            except Exception as e:
                messages.error(request, f"Error creating account: {str(e)}")
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/register.html', {'form': form})

@login_required
def marketplace(request):
    query = request.GET.get('q')
    category_id = request.GET.get('category')
    
    products = Product.objects.filter(is_available=True)
    
    if query:
        products = products.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) |
            Q(category__name__icontains=query)
        )
    
    if category_id:
        products = products.filter(category_id=category_id)
    
    categories = Category.objects.all()
    
    context = {
        'products': products,
        'categories': categories,
        'query': query,
        'selected_category': category_id
    }
    return render(request, 'marketplace/marketplace.html', context)

@login_required
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    context = {'product': product}
    return render(request, 'marketplace/product_detail.html', context)

@login_required
def add_product(request):
    if not request.user.is_farmer():
        messages.warning(request, "Only farmers can add products")
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
            messages.success(request, "Product updated successfully!")
            return redirect('farmer_dashboard')
    else:
        form = ProductForm(instance=product)
    
    return render(request, 'marketplace/edit_product.html', {'form': form, 'product': product})

@login_required
def delete_product(request, pk):
    if not request.user.is_farmer():
        messages.error(request, "Only farmers can delete products.")
        return redirect('marketplace')
    
    product = get_object_or_404(Product, pk=pk, farmer=request.user)
    
    if request.method == 'POST':
        product.delete()
        messages.success(request, "Product deleted successfully!")
        return redirect('farmer_dashboard')
    
    return render(request, 'marketplace/delete_product.html', {'product': product})

@login_required
def add_to_cart(request, product_id):
    if not request.user.is_buyer():
        messages.error(request, "Only buyers can add items to cart.")
        return redirect('marketplace')
    
    product = get_object_or_404(Product, pk=product_id, is_available=True)
    
    # Get or create cart for the buyer
    cart, created = Cart.objects.get_or_create(buyer=request.user)
    
    # Check if product already in cart
    cart_item, item_created = CartItem.objects.get_or_create(
        cart=cart, 
        product=product,
        defaults={'quantity': 1}
    )
    
    if not item_created:
        # If item already in cart, increase quantity
        if cart_item.quantity < product.quantity:
            cart_item.quantity += 1
            cart_item.save()
            messages.success(request, f"Added another {product.name} to your cart.")
        else:
            messages.error(request, f"Cannot add more {product.name}. Only {product.quantity} available.")
    else:
        messages.success(request, f"Added {product.name} to your cart.")
    
    return redirect('view_cart')

@login_required
def view_cart(request):
    if not request.user.is_buyer():
        messages.error(request, "Only buyers can view cart.")
        return redirect('marketplace')
    
    cart, created = Cart.objects.get_or_create(buyer=request.user)
    
    context = {
        'cart': cart,
        'cart_items': cart.items.all()
    }
    return render(request, 'marketplace/cart.html', context)

@login_required
def update_cart_item(request, item_id):
    if not request.user.is_buyer():
        messages.error(request, "Only buyers can update cart.")
        return redirect('marketplace')
    
    cart_item = get_object_or_404(CartItem, pk=item_id, cart__buyer=request.user)
    
    if request.method == 'POST':
        action = request.POST.get('action')
        
        if action == 'increase':
            if cart_item.quantity < cart_item.product.quantity:
                cart_item.quantity += 1
                cart_item.save()
                messages.success(request, f"Increased {cart_item.product.name} quantity.")
            else:
                messages.error(request, f"Cannot add more {cart_item.product.name}. Only {cart_item.product.quantity} available.")
        elif action == 'decrease':
            if cart_item.quantity > 1:
                cart_item.quantity -= 1
                cart_item.save()
                messages.success(request, f"Decreased {cart_item.product.name} quantity.")
            else:
                cart_item.delete()
                messages.success(request, f"Removed {cart_item.product.name} from cart.")
        elif action == 'remove':
            cart_item.delete()
            messages.success(request, f"Removed {cart_item.product.name} from cart.")
    
    return redirect('view_cart')

@login_required
def place_order(request):
    if not request.user.is_buyer():
        messages.error(request, "Only buyers can place orders.")
        return redirect('marketplace')
    
    cart, created = Cart.objects.get_or_create(buyer=request.user)
    
    if cart.items.count() == 0:
        messages.error(request, "Your cart is empty.")
        return redirect('marketplace')
    
    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            # Create an order for each cart item
            for item in cart.items.all():
                order = Order(
                    buyer=request.user,
                    product=item.product,
                    quantity=item.quantity,
                    price_at_order=item.product.price,
                    total_price=item.total_price,
                    payment_method=form.cleaned_data['payment_method'],
                    delivery_address=form.cleaned_data['delivery_address']
                )
                order.save()
                
                # Update product quantity
                product = item.product
                product.quantity -= item.quantity
                if product.quantity <= 0:
                    product.is_available = False
                product.save()
            
            # Clear cart
            cart.items.all().delete()
            
            messages.success(request, "Order placed successfully! The farmer will contact you soon.")
            return redirect('buyer_dashboard')
    else:
        form = OrderForm()
    
    context = {
        'cart': cart,
        'form': form
    }
    return render(request, 'marketplace/place_order.html', context)

@login_required
def farmer_dashboard(request):
    if not request.user.is_farmer():
        messages.error(request, "Only farmers can access this page.")
        return redirect('marketplace')
    
    products = Product.objects.filter(farmer=request.user)
    orders = Order.objects.filter(product__farmer=request.user)
    
    context = {
        'products': products,
        'orders': orders
    }
    return render(request, 'marketplace/farmer_dashboard.html', context)

@login_required
def buyer_dashboard(request):
    if not request.user.is_buyer():
        messages.error(request, "Only buyers can access this page.")
        return redirect('marketplace')
    
    orders = Order.objects.filter(buyer=request.user)
    total_spent = sum(order.total_price for order in orders)
    
    # Get favorite farmers (farmers whose products the buyer has ordered)
    favorite_farmers = CustomUser.objects.filter(
        products__orders__buyer=request.user
    ).distinct()
    
    context = {
        'orders': orders,
        'total_spent': total_spent,
        'favorite_farmers': favorite_farmers
    }
    return render(request, 'marketplace/buyer_dashboard.html', context)

def custom_logout(request):
        logout(request)
        return redirect('login')    

class CustomLoginView(LoginView):
    template_name = 'registration/login.html'
    redirect_authenticated_user = True
    
    def form_valid(self, form):
        messages.success(self.request, f"Welcome back, {form.get_user().username}!")
        return super().form_valid(form)
    
    def form_invalid(self, form):
        messages.error(self.request, "Invalid username or password. Please try again.")
        return super().form_invalid(form)
    
    # Add this method to ensure redirect to marketplace
    def get_success_url(self):
        return reverse('marketplace')

    


                                                                          
