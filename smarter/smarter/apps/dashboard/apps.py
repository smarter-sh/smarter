"""Django app configuration for the dashboard app."""

import logging

from django.apps import AppConfig

from .const import namespace as app_name


logger = logging.getLogger(__name__)


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

        logger.info("Dashboard app ready: signals and receivers imported")
