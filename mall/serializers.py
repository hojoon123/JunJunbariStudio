# serializers.py
from rest_framework import serializers
from mall.models import (
    Category,
    Product,
    ProductImage,
    ProductOption,
    CartProduct,
    Order,
    OrderedProduct,
    Comment,
    OrderPayment, SubDetailCategory, SubCategory,
)


class SubDetailCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubDetailCategory
        fields = ['id', 'name']


class SubCategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = SubCategory
        fields = ['id', 'name']


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = '__all__'


class ProductImageSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductImage
        fields = "__all__"


class ProductOptionSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProductOption
        fields = "__all__"


class ProductBannerSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'keywords', 'description', 'images']

class ProductListSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)

    class Meta:
        model = Product
        fields = ['id', 'name', 'price', 'images', 'review_count', 'review_score']

class ProductSerializer(serializers.ModelSerializer):
    images = ProductImageSerializer(many=True, read_only=True)
    options = ProductOptionSerializer(many=True, read_only=True)
    main_image_url = serializers.ReadOnlyField()
    shipping_info = serializers.CharField(allow_blank=True, allow_null=True)
    category = serializers.PrimaryKeyRelatedField(queryset=Category.objects.all())
    subcategory = serializers.PrimaryKeyRelatedField(queryset=SubCategory.objects.all())
    sub_detail_category = serializers.PrimaryKeyRelatedField(queryset=SubDetailCategory.objects.all())


    class Meta:
        model = Product
        fields = "__all__"


class CartProductSerializer(serializers.ModelSerializer):
    option = serializers.PrimaryKeyRelatedField(
        queryset=ProductOption.objects.all(), required=False, allow_null=True
    )
    total_amount = serializers.SerializerMethodField()
    main_image = serializers.SerializerMethodField()

    class Meta:
        model = CartProduct
        fields = ['id', 'user', 'product', 'option', 'quantity', 'total_amount', 'main_image']

    def get_total_amount(self, obj):
        # CartProduct 모델의 total_price 속성을 활용해 총 금액을 계산합니다.
        return obj.total_price

    def get_main_image(self, obj):
        # 상품의 첫 번째 이미지를 반환
        first_image = obj.product.images.first()
        if first_image:
            return first_image.image.url
        return None

# 구매자용 주문 목록 조회 시 사용
class OrderedProductSerializer(serializers.ModelSerializer):
    option_name = serializers.CharField(source="option.name", allow_null=True)
    total_price = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    class Meta:
        model = OrderedProduct
        fields = ['id', 'product_name', 'option_name', 'quantity', 'price', 'total_price', 'product_image']
    def get_total_price(self, obj):
        return obj.price * obj.quantity
    def get_product_image(self, obj):
        first_image = obj.product.images.first()
        return first_image.image.url if first_image else None
# 판매자용 주문 목록 조회 시 사용
class OrderedProductForSellerSerializer(serializers.ModelSerializer):
    option_name = serializers.CharField(source="option.name", allow_null=True)
    total_price = serializers.SerializerMethodField()
    product_image = serializers.SerializerMethodField()
    buyer = serializers.SerializerMethodField()

    class Meta:
        model = OrderedProduct
        fields = ['id', 'product_name', 'option_name', 'quantity', 'price', 'total_price', 'product_image', 'buyer']

    def get_total_price(self, obj):
        return obj.price * obj.quantity

    def get_product_image(self, obj):
        first_image = obj.product.images.first()
        return first_image.image.url if first_image else None

    def get_buyer(self, obj):
        return {
            'id': obj.order.user.id,
            'username': obj.order.user.username,
            'email': obj.order.user.email
        }


# 주문 목록을 보여줄 때 사용
class OrderCompactSerializer(serializers.ModelSerializer):
    ordered_products_count = serializers.SerializerMethodField()
    first_product_image = serializers.SerializerMethodField()
    first_product_name = serializers.SerializerMethodField()
    class Meta:
        model = Order
        fields = ['id', 'total_amount', 'status', 'created_at', 'first_product_image', 'first_product_name', 'ordered_products_count']
    def get_ordered_products_count(self, obj):
        return obj.ordered_products.count()

    def get_first_product_image(self, obj):
        # 첫 번째 상품의 이미지를 반환
        first_product = obj.ordered_products.first()
        if first_product:
            first_image = first_product.product.images.first()
            return first_image.image.url if first_image else None
        return None
    def get_first_product_name(self, obj):
        first_product = obj.ordered_products.first()
        if not first_product:
            return None
        count = obj.ordered_products.count()
        if count > 1:
            return f"{first_product.product.name} 외 {count - 1}건"
        return first_product.product.name

# 주문 상세 정보 조회 시 사용
class OrderDetailSerializer(serializers.ModelSerializer):
    ordered_products = OrderedProductSerializer(many=True)
    class Meta:
        model = Order
        fields = ['id', 'total_amount', 'status', 'created_at', 'ordered_products']

#TODO: 판매자가 자신의 상품이 포함된 주문 내역을 조회할 때 사용 이거 수정 필요함. 주문 내역 전체를 보는거면 안됨.
class SellerOrderSerializer(serializers.ModelSerializer):
    ordered_products = serializers.SerializerMethodField()
    class Meta:
        model = Order
        fields = ['id', 'total_amount', 'status', 'created_at', 'ordered_products']
    def get_ordered_products(self, obj):
        # 판매자가 판매한 상품만 반환
        user = self.context['request'].user
        ordered_products = obj.ordered_products.filter(product__seller=user)
        return OrderedProductForSellerSerializer(ordered_products, many=True).data

class CommentSerializer(serializers.ModelSerializer):
    class Meta:
        model = Comment
        fields = "__all__"


class OrderPaymentSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderPayment
        fields = "__all__"
