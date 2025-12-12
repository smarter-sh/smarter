"""Account app configuration."""

import logging

from django.apps import AppConfig


logger = logging.getLogger(__name__)


class AccountConfig(AppConfig):
    """Account app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.account"
    verbose_name = "Smarter Account"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa: F401
        from . import signals  # noqa: F401

        logger.info("Account app ready: signals and receivers imported")
