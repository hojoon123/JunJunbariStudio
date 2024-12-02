from django.contrib.auth import authenticate, login, get_user_model, logout
from django.db import IntegrityError, transaction
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt
from rest_framework.exceptions import ValidationError
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, viewsets, generics
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated, BasePermission, AllowAny
from rest_framework.decorators import action
from .models import LoginHistory
from .permissions import DebugAuthentication
from .serializers import UserSerializer


# 현재 프로젝트에서 사용 중인 유저 모델을 가져옵니다.
User = get_user_model()


# 회원가입
class RegisterView(APIView):
    permission_classes = [AllowAny]  # 인증 없이 접근 가능

    @transaction.atomic  # 트랜잭션 관리
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        try:
            if serializer.is_valid():
                user = serializer.save()
                return Response(
                    {"message": "회원가입이 성공적으로 완료되었습니다."},
                    status=status.HTTP_201_CREATED,
                )
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except IntegrityError as e:
            # 중복된 username이나 email로 인한 에러 처리
            transaction.set_rollback(True)  # 트랜잭션 롤백
            return Response(
                {"error": "이미 존재하는 사용자 이름 또는 이메일입니다."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        except ValidationError as e:
            # 기타 유효성 검사 에러 처리
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            # 기타 예외 처리
            return Response(
                {"error": "서버 에러가 발생했습니다. 잠시 후 다시 시도해 주세요."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )


# 로그인
class LoginView(APIView):
    permission_classes = [AllowAny]  # 인증 없이 접근 가능

    def post(self, request):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(request, username=username, password=password)

        if user is not None:
            login(request, user)
            user.last_login = timezone.now()
            user.save()

            # 로그인 이력 저장
            ip_address = request.META.get("REMOTE_ADDR", "0.0.0.0")
            user_agent = request.META.get("HTTP_USER_AGENT", "unknown")
            LoginHistory.objects.create(
                user=user, ip_address=ip_address, user_agent=user_agent
            )

            # JWT 토큰 발급
            refresh = RefreshToken.for_user(user)
            access_token = str(refresh.access_token)

            response = Response(
                {"message": "로그인 성공"},
                status=status.HTTP_200_OK,
            )

            # access_token을 HttpOnly 쿠키로 저장
            response.set_cookie(
                key="access_token",
                value=access_token,
                httponly=True,
                secure=True,  # HTTPS에서만 전송 로컬
                samesite="None",  # CSRF 방지
                max_age=60 * 30,  # 쿠키 만료 시간 (30분)
                path="/",
                domain=".mnuguide.site",
            )

            # refresh_token도 HttpOnly 쿠키에 저장
            response.set_cookie(
                key="refresh_token",
                value=str(refresh),
                httponly=True,
                secure=True,
                samesite="None",
                max_age=7 * 24 * 60 * 60,  # 쿠키 만료 시간 (1주일)
                path="/",
                domain=".mnuguide.site",
            )

            # 디버깅용 print
            print(f"[DEBUG] Set-Cookie: access_token={access_token}")
            print(f"[DEBUG] Set-Cookie: refresh_token={str(refresh)}")

            return response

        return Response(
            {"error": "잘못된 사용자명 또는 비밀번호입니다."},
            status=status.HTTP_400_BAD_REQUEST,
        )


# 로그아웃
class LogoutView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        try:
            # 로그아웃 처리
            logout(request)

            # 리프레시 토큰 블랙리스트 처리
            cookie_refresh_token = request.COOKIES.get("refresh_token")
            print(f"Request Method: {request.method}")
            print(f"Request Headers: {request.headers}")
            print(request)
            print(f"Request Cookies: {request.COOKIES}")
            print(f"Refresh Token from Cookies: {cookie_refresh_token}")
            if cookie_refresh_token:
                try:
                    refresh_token = RefreshToken(cookie_refresh_token)
                    refresh_token.blacklist()  # 블랙리스트 처리
                except Exception as e:
                    return Response(
                        {"error": "토큰 블랙리스트 처리 실패"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

            # 리프레시 토큰과 액세스 토큰 쿠키 제거
            response = Response({"message": "로그아웃 성공"}, status=status.HTTP_200_OK)
            response.delete_cookie("access_token", domain=".mnuguide.site", path="/")
            response.delete_cookie("refresh_token", domain=".mnuguide.site", path="/")
            print("[DEBUG] Called response.delete_cookie for access_token")
            print("[DEBUG] Called response.delete_cookie for refresh_token")

            return response
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)


# 유저 리스트 조회
class UserListView(generics.ListAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]


# 유저 상세 조회, 수정, 삭제
class UserDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        # 현재 로그인한 유저만 반환
        user = self.request.user

        # 현재 로그인한 유저만 정보를 수정 또는 삭제할 수 있게 설정
        print(f"[DEBUG] GET /users/me/ accessed by user: {user.id} - {user.email}")
        print(user)
        return user


    def delete(self, request, *args, **kwargs):
        user = self.get_object()
        user.delete()
        return Response(
            {"message": "회원 탈퇴가 성공적으로 완료되었습니다."},
            status=status.HTTP_204_NO_CONTENT,
        )


# 구독 접근 권한 확인
class HasSubscriptionAccess(BasePermission):
    def has_permission(self, request, view):
        # 사용자가 해당 기능에 접근할 수 있는지 프로필에서 확인.
        if not hasattr(request.user, "userprofile"):
            return False
        return request.user.userprofile.has_access_to_feature()


# 특정 서비스 제공 ViewSet - 구독 권한에 따른 그거 설정 돈 낸 사람만 좋은 기능 열어주기 할 떄 이거 걸기
@method_decorator(csrf_exempt, name='dispatch')
class SomeServiceViewSet(viewsets.ViewSet):
    permission_classes = [
        IsAuthenticated,
        HasSubscriptionAccess,
    ]  # 인증 및 구독 권한 필요

    @action(detail=False, methods=["get"])
    def some_feature(self, request):
        # 구독 권한을 만족하는 경우에만 접근 가능
        return Response({"message": "Feature accessed successfully!"})


# 유저 구독 플랜 및 프로필 업데이트 뷰
class UpdateSubscriptionView(APIView):
    permission_classes = [IsAuthenticated]

    def patch(self, request):
        user = request.user
        serializer = UserSerializer(
            user, data=request.data, partial=True
        )  # 부분 업데이트 허용

        if serializer.is_valid():
            serializer.save()
            return Response(
                {
                    "message": "프로필이 성공적으로 업데이트되었습니다.",
                    "profile": serializer.data,
                },
                status=status.HTTP_200_OK,
            )

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
