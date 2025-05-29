"""Plugin app configuration."""

from django.apps import AppConfig

from .const import namespace as app_name


class PluginConfig(AppConfig):
    """PluginMeta app configuration."""

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name}"

    # pylint: disable=import-outside-toplevel,unused-import
    def ready(self):
        """Import signals."""
        from . import receivers  # noqa
        from . import signals  # noqa
