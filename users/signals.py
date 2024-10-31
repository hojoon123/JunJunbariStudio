from django.db.models.signals import post_save
from django.dispatch import receiver
from django.conf import settings
from .models import UserProfile


@receiver(post_save, sender=settings.AUTH_USER_MODEL)
def manage_user_profile(sender, instance, created, **kwargs):
    if created:
        if not UserProfile.objects.filter(user=instance).exists():  # 중복 생성 방지
            UserProfile.objects.create(user=instance)
    else:
        # 프로필이 이미 존재하는 경우 저장만 수행
        if hasattr(instance, "userprofile"):
            instance.userprofile.save()
