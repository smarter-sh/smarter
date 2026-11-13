"""Django Config for the Doodle app."""

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .const import namespace as app_name

logger = logging.getLogger(__name__)


class DoodleConfig(AppConfig):
    """Django Config for the Doodle app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name.lower()}"
    verbose_name = f"{SMARTER_APP_NAME} {app_name.capitalize()}"

    def ready(self):
        """Log that the app is ready."""
        logger.debug("%s app is %s", f"{SMARTER_APP_NAME} {app_name.capitalize()}", SmarterReadyState.READY)
