# views.py
from django.db import models
from rest_framework import viewsets, permissions, status
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from mall.models import (
    Category,
    Product,
    ProductImage,
    ProductOption,
    CartProduct,
    Order,
    OrderedProduct,
    Comment,
    OrderPayment, SubCategory, SubDetailCategory,
)
from .permissions import IsAdminOrReadOnly, IsSellerOrAdmin, IsOwnerOrAdmin
from .serializers import (
    CategorySerializer,
    ProductSerializer,
    ProductImageSerializer,
    ProductOptionSerializer,
    CartProductSerializer,
    OrderedProductSerializer,
    CommentSerializer,
    OrderPaymentSerializer, SubCategorySerializer, SubDetailCategorySerializer,
    ProductBannerSerializer, ProductListSerializer, SellerOrderSerializer, OrderCompactSerializer,
    OrderDetailSerializer,
)
from django.conf import settings
from django.shortcuts import get_object_or_404
from mall.tasks import cancel_payment

class CategoryViewSet(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    permission_classes = [IsAdminOrReadOnly]


class SubCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubCategory.objects.all()
    serializer_class = SubCategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        category_id = self.request.query_params.get('category_id')
        if category_id:
            queryset = queryset.filter(category_id=category_id)
        return queryset


class SubDetailCategoryViewSet(viewsets.ModelViewSet):
    queryset = SubDetailCategory.objects.all()
    serializer_class = SubDetailCategorySerializer
    permission_classes = [IsAdminOrReadOnly]

    def get_queryset(self):
        queryset = super().get_queryset()
        subcategory_id = self.request.query_params.get('subcategory_id')
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)
        return queryset


class ProductViewSet(viewsets.ModelViewSet):
    queryset = Product.objects.all()
    permission_classes = [IsSellerOrAdmin]

    def get_queryset(self):
        queryset = super().get_queryset()

        # 카테고리별 필터링
        category_id = self.request.query_params.get('category')
        if category_id:
            queryset = queryset.filter(category_id=category_id)

        # 서브카테고리별 필터링
        subcategory_id = self.request.query_params.get('subcategory')
        if subcategory_id:
            queryset = queryset.filter(subcategory_id=subcategory_id)

        # 서브디테일카테고리별 필터링
        sub_detail_category_id = self.request.query_params.get('sub_detail_category')
        if sub_detail_category_id:
            queryset = queryset.filter(sub_detail_category_id=sub_detail_category_id)

        return queryset

    def paginate_queryset(self, queryset):
        # 동적으로 limit 값 설정 가능
        limit = self.request.query_params.get('limit')
        if limit:
            self.paginator.page_size = min(int(limit), 100)
        return super().paginate_queryset(queryset)

    def get_serializer_class(self):
        if self.action == 'list':
            return ProductListSerializer  # 목록 조회 시 상세 정보 제공
        else:
            return ProductSerializer  # 그 외 상황에서는 전체 정보 제공

    def perform_create(self, serializer):
        # 상품 생성 시 판매자를 현재 요청한 유저로 지정
        serializer.save(seller=self.request.user)

    @action(detail=False, methods=['get'])
    def popular_products(self, request):
        queryset = self.get_queryset().order_by('-sales_count')[:4]
        serializer = ProductBannerSerializer(queryset, many=True)
        return Response(serializer.data)


class ProductImageViewSet(viewsets.ModelViewSet):
    queryset = ProductImage.objects.all()
    serializer_class = ProductImageSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]


class ProductOptionViewSet(viewsets.ModelViewSet):
    queryset = ProductOption.objects.all()
    serializer_class = ProductOptionSerializer
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]

    def get_queryset(self):
        """
        product_id에 대한 옵션만 조회하도록 쿼리셋 필터링
        """
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset


class CartProductViewSet(viewsets.ModelViewSet):
    queryset = CartProduct.objects.all()
    serializer_class = CartProductSerializer
    permission_classes = [permissions.IsAuthenticated, IsOwnerOrAdmin]

    def get_queryset(self):
        # 관리자는 모든 장바구니 조회 가능, 일반 사용자는 본인 것만 조회 가능
        if self.request.user.is_staff:
            return self.queryset
        return self.queryset.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        user = request.user
        product = request.data.get("product")
        option = request.data.get("option")

        # 동일한 user, product, option 조합의 cart 제품이 있는지 확인
        existing_cart_product = CartProduct.objects.filter(
            user=user, product=product, option=option
        ).first()

        if existing_cart_product:
            # 이미 존재하면 수량 업데이트
            existing_cart_product.quantity += int(request.data.get("quantity", 1))
            if existing_cart_product.quantity <= 0:
                existing_cart_product.delete()
            else:
                existing_cart_product.save()
            serializer = self.get_serializer(existing_cart_product)
            return Response(serializer.data)
        else:
            # 없으면 새로 생성
            return super().create(request, *args, **kwargs)

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        self.perform_destroy(instance)
        return Response({"message": "장바구니에서 상품이 삭제되었습니다."}, status=status.HTTP_204_NO_CONTENT)


class OrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        # 로그인한 사용자만 자신의 주문을 볼 수 있음
        return Order.objects.filter(user=self.request.user).distinct()

    def get_serializer_class(self):
        if self.action == 'list':
            return OrderCompactSerializer  # 주문 목록에서는 간단한 뷰
        return OrderDetailSerializer  # 주문 상세 보기에서는 상세 뷰

    def create(self, request, *args, **kwargs):
        user = request.user  # 로그인한 유저 정보 가져오기
        cart_product_ids = request.data.get("cart_products", [])
        cart_products = CartProduct.objects.filter(id__in=cart_product_ids, user=user)

        if not cart_products.exists():
            return Response(
                {"error": "장바구니에 선택된 상품이 없습니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 모델의 create_from_cart 메서드 호출
        order = Order.create_from_cart(user, cart_products)
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        order = self.get_object()
        reason = request.data.get("reason", "취소 요청")

        # 소비자 본인과 판매자만 취소 가능
        if not (request.user == order.user or
                order.ordered_products.filter(product__seller=request.user).exists()):
            return Response({"error": "주문을 취소할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # 전체 주문 취소 요청
        order.cancel(reason)
        return Response({"message": "주문 취소 요청이 접수되었습니다.", "status": order.status})

    @action(detail=True, methods=["post"])
    def approve_cancellation(self, request, pk=None):
        """관리자나 판매자가 최종 취소 승인을 하는 API"""
        order = self.get_object()
        reason = request.data.get("reason", "취소 승인")
        try:
            order.approve_cancellation(reason)
            return Response({"message": "주문이 최종 취소되었습니다.", "status": order.status})
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    @action(detail=True, methods=['post'])
    def request_return(self, request, pk=None):
        """반품 요청 (소비자만 가능)"""
        order = self.get_object()
        if request.user != order.user:
            return Response({"error": "반품 요청 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        try:
            order.request_return()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "반품 요청이 완료되었습니다.", "status": order.status})

class SellerOrderViewSet(viewsets.ModelViewSet):
    queryset = Order.objects.all()
    serializer_class = SellerOrderSerializer # 판매자 전용 시리얼라이저
    permission_classes = [IsAuthenticated, IsSellerOrAdmin]

    def get_queryset(self):
        # 판매자는 자신이 판매한 상품이 포함된 주문만 조회 가능
        return Order.objects.filter(
            ordered_products__product__seller=self.request.user
        ).distinct()

    @action(detail=True, methods=["post"], url_path='cancel_product')
    def cancel_product(self, request, pk=None):
        """
        판매자가 소비자의 취소 요청을 승인하면, 주문 상태를 최종 취소 상태로 변경합니다.
        """
        order = self.get_object()

        # 판매자만 취소 승인 가능
        if not order.ordered_products.filter(product__seller=request.user).exists():
            return Response({"error": "취소할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        # 결제 취소 후 상태를 CANCELLED로 변경
        for payment in order.payments.all():
            cancel_payment.delay(payment.id, "판매자 승인에 따른 주문 취소")

        order.status = Order.Status.CANCELLED
        order.save()

        return Response({
            "message": f"주문 {order.id}가 취소되었습니다.",
            "status": order.status
        })

    @action(detail=False, methods=['get'], url_path='search')
    def search_buyer_orders(self, request):
        """
        판매자가 구매자의 ID 또는 이메일로 주문 내역을 조회하는 API
        """
        buyer_id = request.query_params.get('buyer_id')
        buyer_email = request.query_params.get('buyer_email')

        if not buyer_id and not buyer_email:
            return Response({"error": "buyer_id 또는 buyer_email이 필요합니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 구매자 ID 또는 이메일로 주문 필터링
        queryset = self.get_queryset()

        if buyer_id:
            queryset = queryset.filter(user__id=buyer_id)
        elif buyer_email:
            queryset = queryset.filter(user__email=buyer_email)

        if not queryset.exists():
            return Response({"message": "해당 조건에 맞는 주문이 없습니다."}, status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["post"])
    def mark_as_prepared(self, request, pk=None):
        order = self.get_object()
        # 판매자만 상태 변경 가능
        if not order.ordered_products.filter(product__seller=self.request.user).exists():
            return Response({"error": "상태를 변경할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        try:
            order.mark_as_prepared()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "주문이 상품 준비 중으로 변경되었습니다."})

    @action(detail=True, methods=["post"])
    def mark_as_shipped(self, request, pk=None):
        order = self.get_object()
        # 판매자만 상태 변경 가능
        if not order.ordered_products.filter(product__seller=self.request.user).exists():
            return Response({"error": "상태를 변경할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        try:
            order.mark_as_shipped()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "주문이 배송 중으로 변경되었습니다."})

    @action(detail=True, methods=["post"])
    def mark_as_delivered(self, request, pk=None):
        order = self.get_object()
        # 판매자만 상태 변경 가능
        if not order.ordered_products.filter(product__seller=self.request.user).exists():
            return Response({"error": "상태를 변경할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)
        try:
            order.mark_as_delivered()
        except ValueError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        return Response({"message": "주문이 배송 완료로 변경되었습니다."})

    @action(detail=True, methods=["post"], url_path='cancel_product')
    def cancel_product(self, request, pk=None):
        """판매자가 개별 상품 취소를 승인합니다."""
        order = self.get_object()
        seller = request.user

        ordered_product = order.ordered_products.filter(product__seller=seller).first()

        if not ordered_product:
            return Response({"error": "취소할 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        ordered_product.status = OrderedProduct.Status.CANCELLED
        ordered_product.save()

        return Response(
            {"message": f"{ordered_product.product.name} 상품 취소가 완료되었습니다.", "status": ordered_product.status})

    @action(detail=True, methods=["post"], url_path='process-return')
    def process_return(self, request, pk=None):
        """판매자가 반품 요청을 처리합니다."""
        order = self.get_object()
        ordered_product = order.ordered_products.filter(product__seller=self.request.user).first()

        if not ordered_product:
            return Response({"error": "반품 처리 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        ordered_product.process_return()
        return Response(
            {"message": f"{ordered_product.product.name} 반품 처리가 완료되었습니다.", "status": ordered_product.status})

    @action(detail=True, methods=["post"], url_path='process-refund')
    def process_refund(self, request, pk=None):
        """판매자가 환불 처리를 합니다."""
        order = self.get_object()
        ordered_product = order.ordered_products.filter(product__seller=self.request.user).first()

        if not ordered_product:
            return Response({"error": "환불 처리 권한이 없습니다."}, status=status.HTTP_403_FORBIDDEN)

        ordered_product.process_refund()
        return Response(
            {"message": f"{ordered_product.product.name} 환불 처리가 완료되었습니다.", "status": ordered_product.status})

class OrderedProductViewSet(viewsets.ModelViewSet):
    queryset = OrderedProduct.objects.all()
    serializer_class = OrderedProductSerializer
    permission_classes = [permissions.IsAuthenticated]

    @action(detail=True, methods=["post"], url_path='cancel')
    def cancel(self, request, pk=None):
        """소비자가 주문 취소 요청을 보냅니다."""
        ordered_product = self.get_object()

        # '취소 요청됨' 상태로 변경
        if ordered_product.status != OrderedProduct.Status.ORDERED:
            return Response({"error": "주문된 상태에서만 취소 요청을 할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # 취소 요청 상태로 변경
        ordered_product.status = OrderedProduct.Status.CANCEL_REQUESTED
        ordered_product.save()

        return Response({"message": "취소 요청이 접수되었습니다.", "status": ordered_product.status})

    @action(detail=True, methods=["post"], url_path='request-return')
    def request_return(self, request, pk=None):
        """소비자가 반품 요청을 보냅니다."""
        ordered_product = self.get_object()

        if ordered_product.status != OrderedProduct.Status.DELIVERED:
            return Response({"error": "배송 완료된 상품만 반품 요청할 수 있습니다."}, status=status.HTTP_400_BAD_REQUEST)

        # '반품 요청됨' 상태로 변경
        ordered_product.status = OrderedProduct.Status.RETURN_REQUESTED
        ordered_product.save()

        return Response({"message": "반품 요청이 접수되었습니다.", "status": ordered_product.status})


class CommentViewSet(viewsets.ModelViewSet):
    queryset = Comment.objects.all()
    serializer_class = CommentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """
        특정 상품에 대한 리뷰를 조회
        """
        queryset = super().get_queryset()
        product_id = self.request.query_params.get('product_id')
        if product_id:
            queryset = queryset.filter(product_id=product_id)
        return queryset

    def create(self, request, *args, **kwargs):
        """
        리뷰 작성 전에 구매 여부 확인.
        """
        product_id = request.data.get('product_id')
        product = get_object_or_404(Product, pk=product_id)
        user = request.user

        # 모델에서 구매 여부 확인
        if not Comment(product=product, user=user).can_create_review():
            return Response({"error": "해당 상품을 구매한 사용자만 리뷰를 작성할 수 있습니다."}, status=status.HTTP_403_FORBIDDEN)

        # 리뷰 작성
        return super().create(request, *args, **kwargs)


class OrderPaymentViewSet(viewsets.ModelViewSet):
    queryset = OrderPayment.objects.all()
    serializer_class = OrderPaymentSerializer
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request, *args, **kwargs):
        """
        결제 생성 API.
        order의 총 금액을 가져와 자동으로 desired_amount 설정.
        사용자 이름과 이메일도 자동으로 설정됨.
        """
        order_id = request.data.get("order")
        order = get_object_or_404(Order, pk=order_id)

        # OrderPayment 생성
        payment = OrderPayment.create_by_order(order)
        payment_serializer = self.get_serializer(payment)
        return Response(payment_serializer.data, status=status.HTTP_201_CREATED)

    @action(detail=False, methods=["post"], permission_classes=[permissions.AllowAny])
    def webhook(self, request):
        """
        PortOne webhook을 처리하는 엔드포인트.
        IP 제한 설정 및 payload 확인을 통해 결제 상태를 처리.
        """
        # IP 허용 목록 체크
        allowed_ips = getattr(settings, 'ALLOWED_WEBHOOK_IPS', [])
        client_ip = request.META.get("REMOTE_ADDR")
        if not client_ip or client_ip not in allowed_ips:
            return Response(
                {"error": "허용되지 않은 IP에서의 요청입니다."}, status=status.HTTP_403_FORBIDDEN
            )

        payload = request.data
        merchant_uid = payload.get("data", {}).get("paymentId")

        if not merchant_uid:
            return Response(
                "merchant_uid 인자가 누락되었습니다.",
                status=status.HTTP_400_BAD_REQUEST,
            )

        # 결제 내역 확인
        try:
            payment = get_object_or_404(OrderPayment, uid=merchant_uid)
            payment.portone_check()  # 결제 상태 확인 및 업데이트

            # 결제 성공 여부에 따른 응답
            if payment.is_paid_ok:
                return Response({"status": "ok", "is_paid": True, "message": "결제가 완료되었습니다."})
            else:
                return Response({"status": "ok", "is_paid": False, "message": "결제가 실패했습니다."})

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
