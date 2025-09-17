from django.contrib import admin
from .models import CustomUser, Category, Product, Cart, CartItem, Order

@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ['username', 'email', 'user_type', 'location', 'created_at']
    list_filter = ['user_type', 'created_at']
    search_fields = ['username', 'email', 'location']

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'description']
    search_fields = ['name']

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ['name', 'farmer', 'category', 'price', 'quantity', 'is_available', 'created_at']
    list_filter = ['category', 'is_available', 'created_at']
    search_fields = ['name', 'farmer__username']

@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ['buyer', 'created_at', 'updated_at']
    search_fields = ['buyer__username']

@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = ['cart', 'product', 'quantity']
    search_fields = ['cart__buyer__username', 'product__name']

@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['id', 'buyer', 'product', 'quantity', 'total_price', 'payment_method', 'status', 'order_date']
    list_filter = ['payment_method', 'status', 'order_date']
    search_fields = ['buyer__username', 'id']