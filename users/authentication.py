from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, AuthenticationFailed


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        print("[DEBUG] CustomJWTAuthentication 호출됨")
        print("[DEBUG] 요청 헤더:", request.headers)
        print("[DEBUG] 요청 쿠키:", request.COOKIES)

        # 1. 쿠키에서 access_token 확인
        access_token = request.COOKIES.get("access_token")
        if access_token:
            try:
                # 토큰 검증
                validated_token = self.get_validated_token(access_token)
                print("[DEBUG] Access token 쿠키에서 검증 성공")
                return self.get_user(validated_token), validated_token
            except InvalidToken as e:
                print(f"[DEBUG] Access token 검증 실패: {str(e)}")
                raise AuthenticationFailed("Invalid access token from cookies")

        print("[DEBUG] Access token 쿠키에서 찾을 수 없음 JWT 기본 인증으로 넘어감.")
        # 2. 쿠키에 토큰이 없으면 기본 동작 수행 (Authorization 헤더에서 토큰 확인)
        return super().authenticate(request)
