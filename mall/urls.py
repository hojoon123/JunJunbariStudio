# urls.py
from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import (
    CategoryViewSet,
    ProductViewSet,
    ProductImageViewSet,
    ProductOptionViewSet,
    CartProductViewSet,
    OrderViewSet,
    OrderedProductViewSet,
    CommentViewSet,
    OrderPaymentViewSet, SubCategoryViewSet, SubDetailCategoryViewSet, SellerOrderViewSet,
)

router = DefaultRouter()
router.register(r'categories', CategoryViewSet)
router.register(r'subcategories', SubCategoryViewSet)
router.register(r'sub-detail-categories', SubDetailCategoryViewSet)
router.register(r"products", ProductViewSet)
router.register(r"product-images", ProductImageViewSet)
router.register(r"product-options", ProductOptionViewSet)
router.register(r"cart-products", CartProductViewSet)
router.register(r"orders", OrderViewSet, basename='user-order')
router.register(r'seller-orders', SellerOrderViewSet, basename='seller-order')
router.register(r"ordered-products", OrderedProductViewSet)
router.register(r"comments", CommentViewSet)
router.register(r"order-payments", OrderPaymentViewSet)

urlpatterns = [
    path("", include(router.urls)),
    # Webhook endpoint
    path(
        "order-payments/webhook/",
        OrderPaymentViewSet.as_view({"post": "webhook"}),
        name="order-payment-webhook",
    ),
]
