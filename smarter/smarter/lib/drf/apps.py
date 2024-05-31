"""Plugin app configuration."""

from django.apps import AppConfig


class DrfConfig(AppConfig):
    """Django rest framework lib app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.lib.drf"
