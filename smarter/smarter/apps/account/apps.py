# -*- coding: utf-8 -*-
"""Account app configuration."""
from django.apps import AppConfig


class AccountConfig(AppConfig):
    """Account app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.account"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        # import .signals  # noqa
        # import .stripe  # noqa
