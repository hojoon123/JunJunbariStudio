from django.apps import AppConfig


class MallConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "mall"

    def ready(self):
        import mall.signals  # 신호 파일을 import하여 신호를 활성화합니다.
