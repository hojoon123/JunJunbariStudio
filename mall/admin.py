from django.contrib import admin
from .models import (
    Category,
    Product,
    ProductImage,
    ProductOption,
    CartProduct,
    Order,
    OrderedProduct,
    Comment,
    OrderPayment,
)


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("name", "price", "status", "category")
    search_fields = ("name", "description")
    list_filter = ("status", "category")


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("user", "status", "total_amount", "created_at")
    search_fields = ("user__username", "status")
    list_filter = ("status",)


@admin.register(CartProduct)
class CartProductAdmin(admin.ModelAdmin):
    list_display = ("user", "product", "quantity", "total_price")
