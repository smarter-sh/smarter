"""This module is used to configure the Smarter Admin app."""

from django.apps import AppConfig

from .const import namespace as app_name


class ApiConfig(AppConfig):
    """AdminConfig class. This class is used to configure the Smarter Admin app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"

    # pylint: disable=import-outside-toplevel,unused-import
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa
        from . import signals  # noqa
