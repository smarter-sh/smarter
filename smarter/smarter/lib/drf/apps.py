"""Plugin app configuration."""

from django.apps import AppConfig


class DrfConfig(AppConfig):
    """Django rest framework lib app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.lib.drf"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa: F401
