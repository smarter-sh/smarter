"""Django app configuration for the dashboard app."""

from django.utils.text import format_lazy
from django.utils.translation import gettext_lazy as _

from smarter.common.conf import smarter_settings
from smarter.lib.django.apps import SmarterAppConfig

from .const import namespace, presentation_app_name


class WebPlatformConfig(SmarterAppConfig):
    """Django app configuration of the Dashboard app.

    See :class:`~smarter.lib.django.apps.SmarterAppConfig`.
    """

    name = f"smarter.apps.{namespace}"
    verbose_name = format_lazy("{} {}", smarter_settings.platform_branding_app_name, _(presentation_app_name))
