from django.apps import AppConfig


class InteroperabilityConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "interoperability"
    verbose_name = "Healthcare Interoperability"

    def ready(self):
        # Import signal handlers if any
        pass