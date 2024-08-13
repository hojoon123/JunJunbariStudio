# users/urls.py

from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import SomeServiceViewSet, UserViewSet

router = DefaultRouter()
router.register(r"", UserViewSet)

urlpatterns = [
    path("", include(router.urls)),
    path(
        "service/some_feature/",
        SomeServiceViewSet.as_view({"get": "some_feature"}),
        name="some_feature",
    ),
]
