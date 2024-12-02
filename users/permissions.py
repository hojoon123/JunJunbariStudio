from rest_framework.permissions import BasePermission

class DebugAuthentication(BasePermission):
    def has_permission(self, request, view):
        # 쿠키 확인
        cookies = request.COOKIES
        print(f"[DEBUG] Request Cookies for DebugAuthentication: {cookies}")

        # 원래 IsAuthenticated 로직 적용
        return request.user and request.user.is_authenticated
