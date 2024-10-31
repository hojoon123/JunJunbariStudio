from django.core.exceptions import ValidationError, ObjectDoesNotExist
from django.db import transaction, IntegrityError

from .models import CustomUser
from rest_framework import serializers
from .models import UserProfile, SubscriptionPlan


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ["subscription_plan"]


class UserSerializer(serializers.ModelSerializer):
    userprofile = UserProfileSerializer(required=False)

    class Meta:
        model = CustomUser
        fields = [
            "id",
            "first_name",
            "last_name",
            "username",
            "email",
            "password",
            "is_seller",
            "userprofile",
            "date_joined",
            "last_login",
        ]
        extra_kwargs = {
            "password": {"write_only": True},  # 비밀번호는 쓰기 전용으로 처리
        }

    @transaction.atomic
    def create(self, validated_data):
        profile_data = validated_data.pop("userprofile", {})
        password = validated_data.pop("password")
        is_seller = validated_data.get('is_seller', False)

        try:
            user = CustomUser.objects.create(**validated_data)
            user.set_password(password)
            user.is_seller = is_seller
            user.save()
            return user
        except IntegrityError:
            raise ValidationError("이미 존재하는 사용자 이름 또는 이메일입니다.")

    def update(self, instance, validated_data):
        profile_data = validated_data.pop("userprofile", {})
        subscription_plan = profile_data.get("subscription_plan")

        password = validated_data.pop("password", None)
        instance = super().update(instance, validated_data)

        if password:
            instance.set_password(password)
            instance.save()

        # Update UserProfile
        profile = instance.userprofile
        if subscription_plan:
            profile.subscription_plan = subscription_plan
        profile.save()

        return instance
