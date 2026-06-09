"""
Django app configuration for the dashboard app.

This module defines the :class:`WebPlatformConfig` ``AppConfig`` subclass
that registers the dashboard application with Django. On startup it imports
the app's signal receivers so that all signal handlers are connected before
any requests are processed.

Classes:
    WebPlatformConfig: ``AppConfig`` for the ``smarter.apps.dashboard``
        application.
"""

import logging

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins import SmarterHelperMixin

from .const import namespace as app_name

logger = logging.getLogger(__name__)


class WebPlatformConfig(AppConfig, SmarterHelperMixin):
    """
    ``AppConfig`` for the ``smarter.apps.dashboard`` application.

    Extends both :class:`~django.apps.AppConfig` and
    :class:`~smarter.common.mixins.SmarterHelperMixin`.

    Attributes:
        default_auto_field (str): ``"django.db.models.BigAutoField"``
        name (str): Fully qualified app name derived from
            :data:`.const.namespace`, e.g. ``"smarter.apps.dashboard"``.
        verbose_name (str): Human-readable name shown in the Django admin,
            e.g. ``"Smarter Dashboard"``.
    """

    default_auto_field = "django.db.models.BigAutoField"
    name = f"smarter.apps.{app_name.lower()}"
    verbose_name = f"{SMARTER_APP_NAME} {app_name.capitalize()}"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """
        Perform app initialisation after the Django registry is fully populated.

        Imports :mod:`.receivers` and :mod:`.signals` so that all signal
        handlers are registered before any requests are processed. Called
        automatically by Django during startup.
        """
        from . import receivers  # noqa: F401
        from . import signals  # noqa: F401

        logger.debug("%s app is %s", f"{SMARTER_APP_NAME} {app_name.capitalize()}", self.formatted_state_ready)
