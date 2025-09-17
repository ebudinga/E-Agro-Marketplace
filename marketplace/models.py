from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.exceptions import ValidationError
from django.utils import timezone
from django.conf import settings
import random
import string

class CustomUser(AbstractUser):
    USER_TYPE_CHOICES = (
        ('FARMER', 'Farmer'),
        ('BUYER', 'Buyer'),
    )
    user_type = models.CharField(max_length=10, choices=USER_TYPE_CHOICES, default='BUYER')
    phone_number = models.CharField(max_length=15, blank=True)
    address = models.TextField(blank=True)
    location = models.CharField(max_length=100, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def is_farmer(self):
        return self.user_type == 'FARMER'

    def is_buyer(self):
        return self.user_type == 'BUYER'

    def __str__(self):
        return f"{self.username} ({self.get_user_type_display()})"

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='categories/', blank=True, null=True)
    
    class Meta:
        verbose_name_plural = "Categories"
    
    def __str__(self):
        return self.name

class Product(models.Model):
    farmer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='products')
    category = models.ForeignKey(Category, on_delete=models.SET_NULL, null=True, blank=True)
    name = models.CharField(max_length=100)
    description = models.TextField()
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    image = models.ImageField(upload_to='products/')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_available = models.BooleanField(default=True)

    def __str__(self):
        return self.name

class Cart(models.Model):
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='cart')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    @property
    def total_price(self):
        return sum(item.total_price for item in self.items.all())

    def __str__(self):
        return f"Cart of {self.buyer.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)

    @property
    def total_price(self):
        return self.product.price * self.quantity

    def clean(self):
        if self.quantity > self.product.quantity:
            raise ValidationError("Requested quantity exceeds available stock")

    def save(self, *args, **kwargs):
        self.clean()
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.quantity} x {self.product.name}"

class Order(models.Model):
    PAYMENT_CHOICES = [
        ('CASH', 'Cash on Delivery'),
        ('MOBILE', 'Mobile Money')
    ]
    STATUS_CHOICES = [
        ('PENDING', 'Pending'),
        ('CONFIRMED', 'Confirmed'),
        ('SHIPPED', 'Shipped'),
        ('DELIVERED', 'Delivered'),
        ('CANCELLED', 'Cancelled')
    ]
    
    # Add the order_id field before other fields
    order_id = models.CharField(max_length=10, unique=True, blank=True, editable=False)
    
    buyer = models.ForeignKey(CustomUser, on_delete=models.CASCADE, related_name='orders')
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='orders')
    quantity = models.PositiveIntegerField()
    price_at_order = models.DecimalField(max_digits=10, decimal_places=2)
    total_price = models.DecimalField(max_digits=10, decimal_places=2)
    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='PENDING')
    delivery_address = models.TextField()
    order_date = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def generate_order_id(self):
        """Generate a unique order ID"""
        while True:
            new_id = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
            if not Order.objects.filter(order_id=new_id).exists():
                return new_id
    
    def save(self, *args, **kwargs):
        # Generate a random order ID if it doesn't exist
        if not self.order_id:
            # Create a random 8-character alphanumeric ID
            self.order_id = ''.join(random.choices(
                string.ascii_uppercase + string.digits, k=8
            ))
        
        # Set the price at the time of ordering
        if not self.price_at_order:
            self.price_at_order = self.product.price
            
        # Calculate total price
        self.total_price = self.price_at_order * self.quantity
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Order #{self.order_id} by {self.buyer.username} for {self.quantity} x {self.product.name}"