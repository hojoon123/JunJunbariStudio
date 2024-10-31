from django.conf import settings
from django.db import models

from django.contrib.auth.models import AbstractUser


class CustomUser(AbstractUser):
    is_seller = models.BooleanField(default=False)
    refund_account_number = models.CharField(max_length=50, null=True, blank=True)
    refund_bank_name = models.CharField(max_length=100, null=True, blank=True)
    def __str__(self):
        return self.username
    def register_refund_account(self, account_number, bank_name):
        self.refund_account_number = account_number
        self.refund_bank_name = bank_name
        self.save()

    class Meta:
        swappable = "AUTH_USER_MODEL"


class LoginHistory(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="login_histories",
    )
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.CharField(max_length=255, null=True, blank=True)
    login_time = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.login_time}"


class SubscriptionPlan(models.TextChoices):
    FREE = "FREE", "Free Plan"
    BASIC = "BASIC", "Basic Plan"
    PRO = "PRO", "Pro Plan"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="userprofile"
    )
    subscription_plan = models.CharField(
        max_length=10,
        choices=SubscriptionPlan.choices,
        default=SubscriptionPlan.FREE,
    )

    def __str__(self):
        return (
            f"{self.user.first_name} {self.user.last_name} - {self.subscription_plan}"
        )

    # 뷰에 있는 거 여기로 옮겨도 될 듯?
    def has_access_to_feature(self):
        """사용자가 구독 플랜에 따라 특정 기능에 접근할 수 있는지 확인하세요"""
        return self.subscription_plan != SubscriptionPlan.FREE
