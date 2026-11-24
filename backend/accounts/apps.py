from django.apps import AppConfig


class AccountsConfig(AppConfig):
    """Configuration for the project's custom user model and auth API."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
