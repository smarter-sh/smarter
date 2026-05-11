"""Plugin app configuration."""

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging

from .const import namespace as app_name

logger = logging.getSmarterLogger(__name__)


class DrfConfig(AppConfig, SmarterHelperMixin):
    """Django rest framework lib app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.lib.drf"
    verbose_name = "Smarter DRF"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa: F401

        logger.debug("%s app is %s", f"{SMARTER_APP_NAME} {app_name.capitalize()}", self.formatted_state_ready)
