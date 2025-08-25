"""Django app configuration for the dashboard app."""

from django.apps import AppConfig

from .const import namespace as app_name


class WebPlatformConfig(AppConfig):
    """Django app configuration for the dashboard app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
    verbose_name = "Smarter Dashboard"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa: F401
        from . import signals  # noqa: F401
