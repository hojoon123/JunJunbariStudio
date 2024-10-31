from django.utils.deprecation import MiddlewareMixin

class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        # 쿠키에서 access_token을 가져와 Authorization 헤더로 설정
        access_token = request.COOKIES.get('access_token')
        if access_token and 'HTTP_AUTHORIZATION' not in request.META:
            request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
