from django.apps import AppConfig


class SimulationConfig(AppConfig):
    """Django application boundary for future simulation services."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "simulation"
