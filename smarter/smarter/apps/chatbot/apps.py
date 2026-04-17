"""Django Config for the ChatBot app."""

import logging

from django.apps import AppConfig

from smarter.common.mixins import SmarterHelperMixin

from .const import namespace as app_name

logger = logging.getLogger(__name__)


class ChatbotConfig(AppConfig, SmarterHelperMixin):
    """Django Config for the ChatBot app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
    verbose_name = "Smarter ChatBot"

    # pylint: disable=C0415,W0611
    def ready(self):
        """Handle signals."""
        from . import receivers  # noqa
        from . import signals  # noqa

        logger.debug("%s app is %s", app_name.capitalize(), self.formatted_state_ready)
