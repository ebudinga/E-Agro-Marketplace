from django.contrib import admin
from .models import (
    CustomUser, Category, Product, Cart, CartItem, Order,
    FarmerSubaccount, PaymentTransaction,
)


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


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ['order_id', 'buyer', 'product', 'quantity', 'total_price',
                    'payment_method', 'payment_status', 'status', 'order_date']
    list_filter = ['payment_method', 'payment_status', 'status', 'order_date']
    search_fields = ['order_id', 'buyer__username', 'payment_reference']


@admin.register(FarmerSubaccount)
class FarmerSubaccountAdmin(admin.ModelAdmin):
    list_display = ['farmer', 'subaccount_code', 'settlement_bank',
                    'account_number', 'percentage_charge', 'is_verified']
    list_filter = ['is_verified']


@admin.register(PaymentTransaction)
class PaymentTransactionAdmin(admin.ModelAdmin):
    list_display = ['reference', 'buyer', 'amount_kobo', 'status', 'created_at', 'paid_at']
    list_filter = ['status', 'created_at']
    search_fields = ['reference', 'buyer__username']