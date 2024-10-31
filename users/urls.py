from django.urls import path
from .views import (
    RegisterView,
    LoginView,
    LogoutView,
    UpdateSubscriptionView,
    SomeServiceViewSet,
    UserListView,
    UserDetailView,
)
from rest_framework_simplejwt.views import TokenRefreshView

urlpatterns = [
    path("register/", RegisterView.as_view(), name="register"),  # 회원가입
    path("login/", LoginView.as_view(), name="login"),  # 로그인
    path("logout/", LogoutView.as_view(), name="logout"),  # 로그아웃
    path(
        "update-subscription/",
        UpdateSubscriptionView.as_view(),
        name="update_subscription",
    ),  # 구독 업데이트
    path(
        "service/some_feature/",
        SomeServiceViewSet.as_view({"get": "some_feature"}),
        name="some_feature",
    ),  # 서비스 기능
    # 유저 관련 엔드포인트
    path("", UserListView.as_view(), name="user-list"),  # 유저 리스트 조회
    path(
        "me/", UserDetailView.as_view(), name="user-detail"
    ),  # 유저 정보 조회, 수정, 탈퇴
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),  # token refresh
]
