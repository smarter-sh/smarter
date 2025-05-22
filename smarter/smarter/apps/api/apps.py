"""This module is used to configure the Smarter Admin app."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """AdminConfig class. This class is used to configure the Smarter Admin app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.api"

    # pylint: disable=import-outside-toplevel,unused-import
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa
        from . import signals  # noqa
