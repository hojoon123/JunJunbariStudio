from django.conf import settings
from django.db import models

class SubscriptionPlan(models.TextChoices):
    FREE = 'free', 'Free'
    BASIC = 'basic', 'Basic'
    PRO = 'pro', 'Pro'

class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    subscription_plan = models.CharField(
        max_length=10,
        choices=SubscriptionPlan.choices,
        default=SubscriptionPlan.FREE,
    )

    def __str__(self):
        return f"{self.user.name} - {self.subscription_plan}"
