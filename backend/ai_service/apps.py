from django.apps import AppConfig


class AiServiceConfig(AppConfig):
    """Django application boundary for future Groq-backed features."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "ai_service"
