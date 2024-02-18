# -*- coding: utf-8 -*-
"""Plugin app configuration."""
import logging

from django.apps import AppConfig


# from smarter.apps.account.signals import new_user_created
# from .utils import user_init

logger = logging.getLogger(__name__)


class PluginConfig(AppConfig):
    """PluginMeta app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.plugin"

    # pylint: disable=import-outside-toplevel,unused-import
    def ready(self):
        """Import signals."""
        import smarter.apps.plugin.signals  # noqa

        # pylint: disable=E1120
        # new_user_created.connect(user_init)

        logger.info("Plugin app is ready")
