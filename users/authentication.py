from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken


class CustomJWTAuthentication(JWTAuthentication):
    def authenticate(self, request):
        print("[DEBUG] CustomJWTAuthentication 호출됨")
        # 쿠키 확인
        print("[DEBUG] 요청 헤더:", request.headers)
        print("[DEBUG] 요청 쿠키:", request.META)

        access_token = request.COOKIES.get("access_token")
        if not access_token:
            print("[DEBUG] Access token 쿠키에 없음.")
            return None

        try:
            validated_token = self.get_validated_token(access_token)
            print("[DEBUG] Token 검증 성공:", validated_token)
            return self.get_user(validated_token), validated_token
        except InvalidToken as e:
            print("[DEBUG] Invalid token:", str(e))
            return None
