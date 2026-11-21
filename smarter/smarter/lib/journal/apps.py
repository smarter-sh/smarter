"""Django app configuration for the journal app."""

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from smarter.common.const import SMARTER_APP_NAME
from smarter.lib.django.apps import SmarterAppConfig

from .const import namespace, presentation_app_name


class JournalConfig(SmarterAppConfig):
    """Django app configuration of the Journal app.

    See :class:`~smarter.lib.django.apps.SmarterAppConfig`.
    """

    name = f"smarter.lib.{namespace}"
    verbose_name = format_lazy("{} {}", SMARTER_APP_NAME, _(presentation_app_name))
