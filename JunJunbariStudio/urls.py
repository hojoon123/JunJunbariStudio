from django.conf.urls.static import static
from django.contrib import admin
from django.urls import path, include

from JunJunbariStudio import settings

urlpatterns = [
    path("admin/", admin.site.urls),
    path("community/", include("community.urls")),
    path("mall/", include("mall.urls")),
    path("users/", include("users.urls")),
]

if settings.DEBUG:
    urlpatterns += [path("__debug__", include("debug_toolbar.urls"))]
    # debug가 거짓이면 빈리스트를 반환
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
