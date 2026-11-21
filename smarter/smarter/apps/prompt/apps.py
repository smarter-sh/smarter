"""Django app for the OpenAI Function Calling app."""

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .const import namespace as app_name

logger = logging.getLogger(__name__)


class PromptConfig(AppConfig):
    """Django Config for the OpenAI Function Calling app."""

    name = f"smarter.apps.{app_name.lower()}"
    verbose_name = f"{SMARTER_APP_NAME} {app_name.capitalize()}"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals, and register the app's journal sources."""
        from . import journal, progress, receivers, signals  # noqa: F401

        journal.register()

        logger.debug("%s app is %s", f"{SMARTER_APP_NAME} {app_name.capitalize()}", SmarterReadyState.READY)
