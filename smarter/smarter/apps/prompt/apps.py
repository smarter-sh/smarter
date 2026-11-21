"""Django app configuration of the Prompt app."""

# pylint: disable=import-outside-toplevel

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from smarter.common.const import SMARTER_APP_NAME
from smarter.lib.django.apps import SmarterAppConfig

from .const import namespace, presentation_app_name


class PromptConfig(SmarterAppConfig):
    """Django app configuration of the Prompt app.

    See :class:`~smarter.lib.django.apps.SmarterAppConfig`.
    """

    name = f"smarter.apps.{namespace}"
    verbose_name = format_lazy("{} {}", SMARTER_APP_NAME, _(presentation_app_name))
    ready_modules = ("journal", "progress", "receivers", "signals")

    def on_ready(self) -> None:
        """Register the app's journal sources."""
        from .journal import register

        register()
