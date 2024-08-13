from django.contrib.auth.models import User

from .serializers import UserSerializer

from rest_framework.decorators import action
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, viewsets

from users.models import SubscriptionPlan

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


class SomeServiceViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def some_feature(self, request):
        if request.user.userprofile.subscription_plan == SubscriptionPlan.FREE:
            return Response({"error": "This feature is available only for basic and pro users."},
                            status=status.HTTP_403_FORBIDDEN)
        return Response({"message": "Feature accessed successfully!"})