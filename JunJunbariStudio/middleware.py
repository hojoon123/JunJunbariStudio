import logging
from django.utils.deprecation import MiddlewareMixin

# 로깅 설정
logger = logging.getLogger(__name__)


class JWTAuthenticationMiddleware(MiddlewareMixin):
    def process_request(self, request):
        try:
            # 헬스 체크 요청 무시
            if request.path.startswith('/health-check'):
                return  # 이 요청은 무시하고 처리하지 않음

            # 쿠키에서 access_token을 가져옴
            access_token = request.COOKIES.get('access_token')
            if access_token:
                if 'HTTP_AUTHORIZATION' not in request.META:
                    request.META['HTTP_AUTHORIZATION'] = f'Bearer {access_token}'
                    logger.info(f"Authorization 헤더 추가됨: Bearer {access_token}")
                else:
                    logger.info("Authorization 헤더가 이미 존재합니다.")
            else:
                logger.warning(f"Access token이 없습니다. 요청 경로: {request.path}")

        except Exception as e:
            logger.error(f"JWTAuthenticationMiddleware 에러: {e}")
            raise
