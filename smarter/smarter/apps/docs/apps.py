"""This module is used to configure the Smarter docs app."""

from logging import getLogger

from django.apps import AppConfig

from .const import namespace as app_name


logger = getLogger(__name__)


class ApiConfig(AppConfig):
    """AdminConfig class. This class is used to configure the Smarter docs app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
    verbose_name = "Smarter Docs"

    def ready(self):
        """Import signals."""

        logger.info("Docs app ready: signals and receivers imported")
