"""Plugin app configuration."""

import logging

from django.apps import AppConfig

from .const import namespace as app_name


logger = logging.getLogger(__name__)


class PluginConfig(AppConfig):
    """PluginMeta app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"
    verbose_name = "Smarter Plugin"

    # pylint: disable=import-outside-toplevel,unused-import
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa
        from . import signals  # noqa

        logger.info("Plugin app ready: signals and receivers imported")
