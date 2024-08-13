from django.contrib.auth.models import User
from rest_framework import serializers
from .models import UserProfile, SubscriptionPlan


class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserProfile
        fields = ['subscription_plan']

class UserSerializer(serializers.ModelSerializer):
    userprofile = UserProfileSerializer(required=False)

    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'userprofile']

    def create(self, validated_data):
        user = User.objects.create(**validated_data)
        return user

    def update(self, instance, validated_data):
        profile_data = validated_data.pop('userprofile', {})
        subscription_plan = profile_data.get('subscription_plan')

        instance = super().update(instance, validated_data)

        # Update UserProfile
        profile = instance.userprofile
        if subscription_plan:
            profile.subscription_plan = subscription_plan
        profile.save()

        return instance
