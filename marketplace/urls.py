from django.urls import path
from . import views
from marketplace import views

urlpatterns = [
    path('', views.marketplace, name='marketplace'),
    path('product/<int:pk>/', views.product_detail, name='product_detail'),
    path('add-product/', views.add_product, name='add_product'),
    path('edit-product/<int:pk>/', views.edit_product, name='edit_product'),
    path('delete-product/<int:pk>/', views.delete_product, name='delete_product'),
    path('add-to-cart/<int:product_id>/', views.add_to_cart, name='add_to_cart'),
    path('cart/', views.view_cart, name='view_cart'),
    path('update-cart/<int:item_id>/', views.update_cart_item, name='update_cart_item'),
    path('place-order/', views.place_order, name='place_order'),
    path('farmer-dashboard/', views.farmer_dashboard, name='farmer_dashboard'),
    path('buyer-dashboard/', views.buyer_dashboard, name='buyer_dashboard'),
    path('logout/', views.custom_logout, name='logout'),
]