"""This module is used to configure the Smarter docs app."""

from logging import getLogger

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins.helper_mixin import SmarterReadyState

from .const import namespace as app_name

logger = getLogger(__name__)


class ApiConfig(AppConfig):
    """AdminConfig class.

    This class is used to configure the Smarter docs app.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name.lower()}"
    verbose_name = f"{SMARTER_APP_NAME} {app_name.capitalize()}"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        from . import receivers, signals  # noqa: F401

        logger.debug("%s app is %s", f"{SMARTER_APP_NAME} {app_name.capitalize()}", SmarterReadyState.READY)
