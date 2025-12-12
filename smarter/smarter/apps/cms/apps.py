"""This module is used to configure the Smarter cms app."""

import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    """AdminConfig class. This class is used to configure the Smarter cms app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.cms"
    verbose_name = "Smarter CMS"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa: F401
        from . import signals  # noqa: F401

        logger.info("CMS app ready: signals and receivers imported")
