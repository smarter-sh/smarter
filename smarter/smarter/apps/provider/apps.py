"""Django app for the Provider app."""

from django.apps import AppConfig


class ProviderConfig(AppConfig):
    """Django Config for the Provider app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.provider"
    verbose_name = "Provider"

    # pylint: disable=C0415,W0611
    def ready(self):
        """Handle signals."""
        from . import receivers  # noqa
        from . import signals  # noqa
