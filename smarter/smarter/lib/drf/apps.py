"""Django app configuration of smarter.lib.drf, which holds API keys and token authentication."""

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .const import namespace as app_name

logger = logging.getSmarterLogger(__name__)


class DrfConfig(AppConfig):
    """Django rest framework lib app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.lib.drf"
    verbose_name = f"{SMARTER_APP_NAME} {app_name.capitalize()}"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Connect the app's signal receivers, by importing them."""
        from . import receivers, signals  # noqa: F401

        logger.debug(
            "%s.DrfConfig.ready() %s app is %s",
            logging.SmarterFormattedText.text(__name__),
            f"{SMARTER_APP_NAME} {app_name.upper()}",
            SmarterReadyState.READY,
        )
