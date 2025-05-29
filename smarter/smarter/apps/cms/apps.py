"""This module is used to configure the Smarter cms app."""

from django.apps import AppConfig


class ApiConfig(AppConfig):
    """AdminConfig class. This class is used to configure the Smarter cms app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.cms"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa: F401
        from . import signals  # noqa: F401
