"""Connection app configuration."""

import logging

from django.apps import AppConfig

from smarter.common.mixins import SmarterHelperMixin

from .const import namespace as app_name

logger = logging.getLogger(__name__)


class ConnectionConfig(AppConfig, SmarterHelperMixin):
    """Connection app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
    verbose_name = "Smarter Connection"

    # pylint: disable=import-outside-toplevel,unused-import
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa
        from . import signals  # noqa

        logger.debug("%s app is %s", app_name.capitalize(), self.formatted_state_ready)
