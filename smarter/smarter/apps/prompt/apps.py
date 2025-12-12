"""Django app for the OpenAI Function Calling app."""

import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class PromptConfig(AppConfig):
    """Django Config for the OpenAI Function Calling app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.prompt"
    verbose_name = "Smarter Prompt"

    # pylint: disable=C0415,W0611
    def ready(self):
        """Handle signals."""
        from . import receivers  # noqa
        from . import signals  # noqa

        logger.info("Prompt app ready: signals and receivers imported")
