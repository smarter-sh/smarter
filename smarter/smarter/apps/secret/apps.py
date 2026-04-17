"""Secret app configuration."""

import logging

from django.apps import AppConfig

from smarter.common.mixins import SmarterHelperMixin

from .const import namespace

logger = logging.getLogger(__name__)


class SecretConfig(AppConfig, SmarterHelperMixin):
    """Secret app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{namespace}"
    verbose_name = f"Smarter {namespace.capitalize()}"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa: F401
        from . import signals  # noqa: F401

        logger.debug("%s app is %s", namespace.capitalize(), self.formatted_state_ready)
