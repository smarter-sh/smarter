"""Django app configuration for the dashboard app."""

from django.apps import AppConfig

from .const import namespace as app_name


class WebPlatformConfig(AppConfig):
    """Django app configuration for the dashboard app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
