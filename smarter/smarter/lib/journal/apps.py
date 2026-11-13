"""Django app configuration for the journal app."""

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .const import namespace as app_name

logger = logging.getLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


class JournalConfig(AppConfig):
    """Django app configuration for the journal app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.lib.journal"
    verbose_name = "Smarter Journal"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import the receivers and signals, which connects the receivers."""
        from . import receivers, signals  # noqa: F401

        app_label = f"{SMARTER_APP_NAME} {app_name.capitalize()}"
        logger.debug("%s.ready() %s app is %s", logger_prefix, app_label, SmarterReadyState.READY)
