from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse  # 헬스 체크 엔드포인트용

from JunJunbariStudio import settings

# 헬스 체크 뷰 함수
def health_check(request):
    return JsonResponse({"status": "ok"})

urlpatterns = [
    path("admin/", admin.site.urls),
    path("community/", include("community.urls")),
    path("mall/", include("mall.urls")),
    path("users/", include("users.urls")),
    path('health-check', health_check),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__", include("debug_toolbar.urls"))]
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
