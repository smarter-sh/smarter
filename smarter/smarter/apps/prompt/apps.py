"""Django app for the OpenAI Function Calling app."""

from django.apps import AppConfig


class PromptConfig(AppConfig):
    """Django Config for the OpenAI Function Calling app."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.apps.prompt"
    verbose_name = "Prompt"

    # pylint: disable=C0415,W0611
    def ready(self):
        """Handle signals."""
        from . import receivers  # noqa
        from . import signals  # noqa
