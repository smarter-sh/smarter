"""This module is used to configure the Smarter docs app."""

from logging import getLogger

from django.apps import AppConfig

from smarter.common.mixins import SmarterHelperMixin

from .const import namespace as app_name

logger = getLogger(__name__)


class ApiConfig(AppConfig, SmarterHelperMixin):
    """AdminConfig class. This class is used to configure the Smarter docs app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
    verbose_name = "Smarter Docs"

    def ready(self):
        """Import signals."""

        logger.debug("%s app is %s", app_name.capitalize(), self.formatted_state_ready)
