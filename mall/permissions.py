from rest_framework import permissions

class IsAdminOrReadOnly(permissions.BasePermission):
    def has_permission(self, request, view):
        # GET 요청은 누구나 허용, 그 외 요청은 관리자만 허용
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff

class IsSellerOrAdmin(permissions.BasePermission):
    def has_permission(self, request, view):
        # 조회는 누구나 가능, 그 외 요청은 판매자나 관리자만 허용
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or request.user.is_seller  # 판매자 또는 관리자

    def has_object_permission(self, request, view, obj):
        # 관리자이거나 해당 상품의 소유자인 경우에만 수정/삭제 가능
        if request.method in permissions.SAFE_METHODS:
            return True
        return request.user.is_staff or obj.seller == request.user  # 관리자이거나 판매자 본인


class IsOwnerOrAdmin(permissions.BasePermission):
    """
    사용자 본인 또는 관리자인 경우에만 접근을 허용하는 권한 클래스.
    """
    def has_object_permission(self, request, view, obj):
        # 요청 사용자가 관리자인 경우 True 반환
        if request.user and request.user.is_staff:
            return True
        # 요청 사용자가 해당 객체의 소유자인 경우 True 반환
        return obj.user == request.user

