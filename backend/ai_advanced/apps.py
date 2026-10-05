from django.apps import AppConfig


class AiAdvancedConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_advanced"
    verbose_name = "Advanced Healthcare AI"

    def ready(self):
        import ai_advanced.signals  # noqa: F401