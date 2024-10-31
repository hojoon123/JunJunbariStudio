import logging
from uuid import uuid4
from typing import List

import requests
from PIL import Image
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import UniqueConstraint
from django.http import Http404
from django_ckeditor_5.fields import CKEditor5Field
from django.db.models import QuerySet
from iamport import Iamport
from rest_framework.reverse import reverse
from mall.tasks import cancel_payment

from JunJunbariStudio import settings


logger = logging.getLogger(__name__)


class Category(models.Model):
    name = models.CharField(max_length=100)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = verbose_name_plural = "상품 분류"

class SubCategory(models.Model):
    name = models.CharField(max_length=100)
    category = models.ForeignKey('Category', related_name='subcategories', on_delete=models.CASCADE)

    def __str__(self):
        return self.name

class SubDetailCategory(models.Model):
    name = models.CharField(max_length=100)
    subcategory = models.ForeignKey('SubCategory', related_name='sub_detail_categories', on_delete=models.CASCADE)

    def __str__(self):
        return self.name


class Product(models.Model):
    class Status(models.TextChoices):
        ACTIVE = ("a", "판매 중")
        INACTIVE = ("i", "판매 중지")
        SOLD_OUT = ("s", "품절")
        OBSOLETE = ("o", "단종")

    category = models.ForeignKey(
        Category, on_delete=models.CASCADE, db_constraint=False, related_name="products", default=1
    )
    subcategory = models.ForeignKey(
        SubCategory, on_delete=models.CASCADE, db_constraint=False, related_name="products", default=1
    )
    sub_detail_category = models.ForeignKey(
        SubDetailCategory, on_delete=models.CASCADE, db_constraint=False, related_name="products", default=1
    )
    name = models.CharField(max_length=100, db_index=True)
    description = CKEditor5Field("설명", config_name="extends")
    price = models.PositiveIntegerField()
    shipping_info = models.TextField("배송 정보", blank=True, null=True)
    status = models.CharField(
        choices=Status.choices, default=Status.ACTIVE, max_length=1
    )
    specifications = models.JSONField("제품 사양", default=dict)
    presentation_image = models.ImageField(
        upload_to="mall/product/presentation/%Y/%m/%d",
        blank=True,
        null=True,
        verbose_name="Presentation 이미지",
    )
    keywords = models.JSONField("제품 키워드", default=list)
    sales_count = models.PositiveIntegerField(default=0)  # 판매량
    view_count = models.PositiveIntegerField(default=0)  # 조회수
    review_count = models.PositiveIntegerField(default=0)  # 작성된 리뷰 수
    review_score = models.FloatField(default=0)  # 리뷰 점수
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"<{self.pk}> {self.name}"

    @property
    def main_image_url(self):
        """Returns the URL of the main presentation image if available."""
        return self.presentation_image.url if self.presentation_image else None

    class Meta:
        verbose_name = verbose_name_plural = "상품"
        ordering = ['-sales_count']  # default 판매량 순으로 정렬


class ProductOption(models.Model):
    product = models.ForeignKey(
        Product, related_name="options", on_delete=models.CASCADE
    )
    name = models.CharField(max_length=100)
    additional_price = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.product.name} - {self.name} (+{self.additional_price}원)"


class ProductImage(models.Model):
    product = models.ForeignKey(
        Product, related_name="images", on_delete=models.CASCADE
    )
    image = models.ImageField(upload_to="mall/product/images/%Y/%m/%d")

    def __str__(self):
        return f"Image for {self.product.name}"

    class Meta:
        verbose_name = "상품 이미지"
        verbose_name_plural = "상품 이미지"


class Comment(models.Model):
    product = models.ForeignKey(
        Product, on_delete=models.CASCADE, related_name="comments"
    )
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    content = models.TextField("리뷰 내용")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.get_full_name() or self.user.name}의 리뷰: {self.content}"

    def can_create_review(self):
        """
        사용자가 해당 상품을 구매했는지 확인하는 메서드.
        """
        return OrderedProduct.objects.filter(order__user=self.user, product=self.product).exists()


class CartProduct(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="cart_products",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_constraint=False)
    option = models.ForeignKey(
        ProductOption, on_delete=models.CASCADE, null=True, blank=True
    )
    quantity = models.PositiveIntegerField(default=1, validators=[MinValueValidator(1)])

    @property
    def total_price(self):
        option_price = self.option.additional_price if self.option else 0
        return (self.product.price + option_price) * self.quantity

    def __str__(self):
        return f"<{self.pk}> {self.product.name} - {self.option.name if self.option else '기본 옵션'} ({self.quantity}개)"

    class Meta:
        verbose_name = verbose_name_plural = "장바구니 상품"
        constraints = [
            UniqueConstraint(
                fields=["user", "product", "option"], name="unique_user_product_option"
            )
        ]


class Order(models.Model):
    class Status(models.TextChoices):
        REQUSETED = ("REQUSETED", "주문 요청")
        PAID = ("PAID", "결제 완료")
        PREPARED_PRODUCT = ("PREPARED_PRODUCT", "상품 준비 중")
        SHIPPED = ("SHIPPED", "배송 중")
        DELIVERED = ("DELIVERED", "배송 완료")
        PARTIAL_REFUNDED = ("PARTIAL_REFUNDED", "일부 환불 완료")
        FULL_REFUNDED = ("FULL_REFUNDED", "전체 환불 완료")
        CANCELLED = ("CANCELLED", "주문 취소")
        CANCEL_REQUESTED = ("CANCEL_REQUESTED", "취소 요청됨")


    uid = models.UUIDField(default=uuid4, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="orders",
    )
    total_amount = models.PositiveIntegerField()
    status = models.CharField(
        choices=Status.choices, default=Status.REQUSETED, max_length=16
    )
    product_set = models.ManyToManyField(Product, through="OrderedProduct", blank=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Order {self.pk} by {self.user.name}"

    def can_pay(self):
        return self.status in (self.Status.REQUSETED)

    @property
    def name(self):
        first_product = self.product_set.first()
        if first_product is None:
            return "주문 상품 없음"
        size = self.product_set.all().count()
        if size < 2:
            return first_product.name
        return f"{first_product.name} 외 {size - 1}건"

    @classmethod
    def create_from_cart(cls, user, cart_products):
        """주문 생성 및 장바구니 항목 삭제 로직"""
        total_amount = sum([cart_product.total_price for cart_product in cart_products])

        # 주문 생성
        order = cls.objects.create(user=user, total_amount=total_amount)

        # 주문된 상품 추가
        ordered_product_list = []
        for cart_product in cart_products:
            ordered_product = OrderedProduct(
                order=order,
                product=cart_product.product,
                option=cart_product.option,
                name=cart_product.product.name,
                price=cart_product.product.price
                      + (cart_product.option.additional_price if cart_product.option else 0),
                quantity=cart_product.quantity,
            )
            ordered_product_list.append(ordered_product)

        OrderedProduct.objects.bulk_create(ordered_product_list)
        cart_products.delete()

        return order

    def cancel(self, reason=""):
        """전체 주문 취소 요청 로직"""
        if self.status in (self.Status.SHIPPED, self.Status.DELIVERED):
            raise ValueError("배송 중이거나 완료된 주문은 취소할 수 없습니다.")

        # 상태를 '취소 요청됨'으로 변경
        self.status = self.Status.CANCEL_REQUESTED
        self.save()

        # 최종 취소 작업은 판매자나 관리자에 의해 수행됨

    def approve_cancellation(self, reason=""):
        """취소 요청 승인 및 결제 취소 처리"""
        if self.status != self.Status.CANCEL_REQUESTED:
            raise ValueError("취소 요청된 주문만 승인 가능합니다.")

        # 결제 취소 처리 로직 (비동기)
        for payment in self.payments.all():
            cancel_payment.delay(payment.id, reason)

        # 주문에 속한 모든 상품의 상태를 취소로 변경
        for ordered_product in self.ordered_products.all():
            ordered_product.cancel()

        self.status = self.Status.CANCELLED
        self.save()

    def check_and_update_order_status(self):
        """주문 상태를 확인하고 필요한 경우 업데이트 (부분 취소 반영)"""
        # 모든 ordered_product가 취소되었는지 확인
        all_cancelled = all(
            op.status == OrderedProduct.Status.CANCELLED for op in self.ordered_products.all()
        )

        if all_cancelled:
            self.status = self.Status.CANCELLED
        else:
            self.status = self.Status.PARTIAL_REFUNDED  # 일부만 취소된 상태로 표시
        self.save()

    def mark_as_prepared(self):
        """상품 준비 중 상태로 변경"""
        if self.status != self.Status.PAID:
            raise ValueError(
                "결제 완료 상태인 주문만 상품 준비 중으로 변경할 수 있습니다."
            )
        self.status = self.Status.PREPARED_PRODUCT
        self.save()

    def mark_as_shipped(self):
        """배송 중 상태로 변경"""
        if self.status != self.Status.PREPARED_PRODUCT:
            raise ValueError(
                "상품 준비 중 상태인 주문만 배송 중으로 변경할 수 있습니다."
            )
        self.status = self.Status.SHIPPED
        self.save()

    def mark_as_delivered(self):
        """배송 완료 상태로 변경"""
        if self.status != self.Status.SHIPPED:
            raise ValueError(
                "배송 중 상태인 주문만 배송 완료 상태로 변경할 수 있습니다."
            )
        self.status = self.Status.DELIVERED
        self.save()


    class Meta:
        ordering = ["-pk"]
        verbose_name = verbose_name_plural = "주문"

class OrderedProduct(models.Model):
    class Status(models.TextChoices):
        ORDERED = "ORDERED", "주문됨"
        SHIPPED = "SHIPPED", "배송 중"
        DELIVERED = "DELIVERED", "배송 완료"
        RETURN_REQUESTED = "RETURN_REQUESTED", "반품 요청됨"
        RETURNED = "RETURNED", "반품 완료"
        REFUNDED = "REFUNDED", "환불 완료"
        CANCEL_REQUESTED = "CANCEL_REQUESTED", "취소 요청됨"
        CANCELLED = "CANCELLED", "취소됨"

    order = models.ForeignKey(
        Order,
        on_delete=models.CASCADE,
        db_constraint=False,
        related_name="ordered_products",
    )
    product = models.ForeignKey(Product, on_delete=models.CASCADE, db_constraint=False)
    option = models.ForeignKey(
        ProductOption, on_delete=models.CASCADE, null=True, blank=True
    )
    name = models.CharField(
        max_length=100, help_text="주문 시점의 상품명을 저장합니다."
    )
    price = models.PositiveIntegerField(help_text="주문 시점의 상품가격을 저장합니다.")
    quantity = models.PositiveIntegerField("수량")
    status = models.CharField(
        max_length=16, choices=Status.choices, default=Status.ORDERED
    )  # 상품 상태 필드 추가
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def cancel(self):
        """개별 상품 취소 로직"""
        if self.status != self.Status.ORDERED:
            raise ValueError("주문된 상태에서만 취소할 수 있습니다.")
        self.status = self.Status.CANCELLED
        self.save()

        # 주문 상태 업데이트
        self.order.check_and_update_order_status()

    def request_return(self):
        """반품 요청 로직"""
        if self.status != self.Status.DELIVERED:
            raise ValueError("배송 완료된 주문만 반품 요청할 수 있습니다.")
        self.status = self.Status.RETURN_REQUESTED
        self.save()

    def process_return(self):
        """반품 처리 로직"""
        if self.status != self.Status.RETURN_REQUESTED:
            raise ValueError("반품 요청 상태에서만 반품 처리가 가능합니다.")
        self.status = self.Status.RETURNED
        self.save()

    def process_refund(self):
        """환불 처리 로직"""
        if self.status != self.Status.RETURNED:
            raise ValueError("반품 완료된 주문만 환불할 수 있습니다.")
        self.status = self.Status.REFUNDED
        self.save()

    class Meta:
        constraints = [
            UniqueConstraint(
                fields=["order", "product", "option"],
                name="unique_order_product_option",
            )
        ]



class AbstarctPortOnePayment(models.Model):
    class PayMethod(models.TextChoices):
        CARD = ("card", "카드 결제")
        VIRUTAL_ACCOUNT = ("virutal_account", "가상계좌 결제")

    class PayStatus(models.TextChoices):
        READY = "READY", "미결제"
        PAID = "PAID", "결제완료"
        CANCELLED = "CANCELLED", "결제취소"
        FAILED = "FAILED", "결제실패"
        VIRTUAL_ACCOUNT_ISSUED = "VIRTUAL_ACCOUNT_ISSUED", "가상계좌"

    meta = models.JSONField("포트원 결제내역", default=dict, editable=False)
    uid = models.UUIDField("쇼핑몰 결제식별자", default=uuid4, editable=False)
    name = models.CharField("결제명", max_length=200, editable=False)
    desired_amount = models.PositiveIntegerField("결제요청금액", editable=False)
    buyer_name = models.CharField("구매자명", max_length=100, editable=False)
    buyer_email = models.EmailField("구매자 이메일", editable=False)
    pay_method = models.CharField(
        choices=PayMethod.choices, max_length=20, default=PayMethod.CARD
    )
    pay_status = models.CharField(
        choices=PayStatus.choices, max_length=22, default=PayStatus.READY
    )
    is_paid_ok = models.BooleanField("결제성공여부", default=False, db_index=True)

    @property
    def merchant_uid(self):
        return str(self.uid)

    def portone_check(self):
        try:
            response = requests.get(
                f"https://api.portone.io/payments/{self.merchant_uid}",
                headers={"Authorization": f"PortOne {settings.PORTONE_API_SECRET}"},
            )
            self.meta = response.json()
            self.pay_status = self.meta["status"]
            self.is_paid_ok = (
                self.pay_status == "PAID"
                and self.meta["amount"]["total"] == self.desired_amount
            )
            self.save()
        except (Iamport.ResponseError, Iamport.HttpError) as e:
            logger.error(str(e), exc_info=e)
            raise Http404("포트원에서 결제 내역을 찾을 수 없습니다.")

    def cancel(self, reason):
        if self.pay_status != self.PayStatus.PAID:
            raise ValueError("결제 완료 상태만 취소할 수 있습니다.")

        url = f"https://api.portone.io/payments/{self.merchant_uid}/cancel"
        payload = {"reason": reason}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"PortOne {settings.PORTONE_API_SECRET}",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200:
                self.pay_status = self.PayStatus.CANCELLED
                self.save()
                self.update_related_statuses_to_cancelled()
            else:
                raise ValueError(
                    f"결제 취소 실패: {response_data.get('message', '알 수 없는 오류')}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(str(e), exc_info=e)
            raise Http404("포트원 결제 취소 요청 중 오류가 발생했습니다.")

    def update_related_statuses_to_cancelled(self):
        """연관된 상태를 취소로 변경하기 위한 메서드. 상속받는 클래스에서 구현해야 합니다."""
        raise NotImplementedError("이 메서드는 상속받는 클래스에서 구현해야 합니다.")

    def handle_cancel_error(self, status_code, response_data):
        """취소 실패 시 발생할 수 있는 오류를 처리합니다."""
        error_message = response_data.get("message", "알 수 없는 오류가 발생했습니다.")

        if status_code == 400:
            raise ValueError(f"잘못된 요청: {error_message}")
        elif status_code == 401:
            raise PermissionError(f"인증 오류: {error_message}")
        elif status_code == 403:
            raise PermissionError(f"요청 거절: {error_message}")
        elif status_code == 404:
            raise ValueError(f"결제 건을 찾을 수 없습니다: {error_message}")
        elif status_code == 409:
            if "PaymentNotPaidError" in error_message:
                raise ValueError("결제가 완료되지 않았습니다.")
            elif "PaymentAlreadyCancelledError" in error_message:
                raise ValueError("결제가 이미 취소되었습니다.")
            elif "CancellableAmountConsistencyBrokenError" in error_message:
                raise ValueError("취소 가능 잔액 검증에 실패했습니다.")
            elif "CancelAmountExceedsCancellableAmountError" in error_message:
                raise ValueError("결제 취소 금액이 취소 가능 금액을 초과했습니다.")
            elif "SumOfPartsExceedsCancelAmountError" in error_message:
                raise ValueError(
                    "면세 금액 등 하위 항목들의 합이 전체 취소 금액을 초과했습니다."
                )
            elif (
                "CancelTaxFreeAmountExceedsCancellableTaxFreeAmountError"
                in error_message
            ):
                raise ValueError(
                    "취소 면세 금액이 취소 가능한 면세 금액을 초과했습니다."
                )
            elif "CancelTaxAmountExceedsCancellableTaxAmountError" in error_message:
                raise ValueError(
                    "취소 과세 금액이 취소 가능한 과세 금액을 초과했습니다."
                )
            elif (
                "RemainedAmountLessThanPromotionMinPaymentAmountError" in error_message
            ):
                raise ValueError(
                    "남은 금액이 프로모션 최소 결제 금액보다 작아질 수 없습니다."
                )
            else:
                raise ValueError(f"취소 실패: {error_message}")
        else:
            raise ValueError(f"취소 실패: {error_message}")

    class Meta:
        abstract = True


class OrderPayment(AbstarctPortOnePayment):
    order = models.ForeignKey(
        Order, on_delete=models.CASCADE, db_constraint=False, related_name="payments"
    )

    @classmethod
    def create_by_order(cls, order: Order) -> "OrderPayment":
        """
        OrderPayment를 생성하는 메서드.
        buyer_name, buyer_email, desired_amount
        order로부터 가져옴.
        """
        return cls.objects.create(
            order=order,
            name=order.name,  # 주문 이름
            desired_amount=order.total_amount,  # 주문 총 금액
            buyer_name=order.user.get_full_name(),  # 주문자 이름
            buyer_email=order.user.email,  # 주문자 이메일
        )

    def portone_check(self):
        """
        PortOne API를 호출하여 결제 상태를 확인하는 메서드.
        결제 성공 시 주문 상태를 PAID로 업데이트.
        """
        try:
            # PortOne API를 호출해 결제 상태 확인
            response = requests.get(
                f"https://api.portone.io/payments/{self.merchant_uid}",
                headers={"Authorization": f"PortOne {settings.PORTONE_API_SECRET}"},
            )
            self.meta = response.json()
            self.pay_status = self.meta["status"]
            self.is_paid_ok = (
                    self.pay_status == "PAID"
                    and self.meta["amount"]["total"] == self.desired_amount
            )
            self.save()

            # 결제 성공 시 주문 상태를 업데이트
            if self.is_paid_ok:
                self.order.status = Order.Status.PAID
                self.order.save()

                # 다른 결제 내역 삭제 (중복 방지)
                self.order.payments.exclude(pk=self.pk).delete()

        except (Iamport.ResponseError, Iamport.HttpError) as e:
            logger.error(str(e), exc_info=e)
            raise Http404("포트원에서 결제 내역을 찾을 수 없습니다.")

    def cancel(self, reason):
        """
        결제 취소 메서드. PortOne API를 통해 취소 요청을 전송.
        """
        if self.pay_status != self.PayStatus.PAID:
            raise ValueError("결제 완료 상태만 취소할 수 있습니다.")

        url = f"https://api.portone.io/payments/{self.merchant_uid}/cancel"
        payload = {"reason": reason}
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"PortOne {settings.PORTONE_API_SECRET}",
        }

        try:
            response = requests.post(url, json=payload, headers=headers)
            response_data = response.json()

            if response.status_code == 200:
                self.pay_status = self.PayStatus.CANCELLED
                self.save()
                self.update_related_statuses_to_cancelled()
            else:
                raise ValueError(
                    f"결제 취소 실패: {response_data.get('message', '알 수 없는 오류')}"
                )
        except requests.exceptions.RequestException as e:
            logger.error(str(e), exc_info=e)
            raise Http404("포트원 결제 취소 요청 중 오류가 발생했습니다.")

    def update_related_statuses_to_cancelled(self):
        """
        결제가 취소되었을 때 주문 상태를 CANCELLED로 변경.
        """
        self.order.status = Order.Status.CANCELLED
        self.order.save()
