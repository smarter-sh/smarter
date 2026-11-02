"""
Django app configuration of the MCPServer app.

The MCPServer app serves the platform's own MCP servers: the Smarter Project MCP server, which
searches and reads The Smarter Project's repositories and blog, and the Smarter Operations MCP
server, which gives the platform's staff read-only tools for operations and the help desk.
:class:`MCPServerConfig` registers the app with Django and connects its signal receivers.

.. note::

    **Experimental.** The MCPServer was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib import logging

from .const import namespace as app_name
from .const import presentation_app_name

logger = logging.getLogger(__name__)


class MCPServerConfig(AppConfig, SmarterHelperMixin):
    """
    Django app configuration of the MCPServer app.

    Django creates it once, at startup, from ``INSTALLED_APPS``. Its :meth:`ready` connects the
    app's signal receivers.
    """

    #: The type of the primary key of the app's models.
    default_auto_field = "django.db.models.BigAutoField"

    #: The app's dotted path, ``smarter.apps.mcpserver``.
    name = f"smarter.apps.{app_name.lower()}"

    #: The app's name in the Django admin, e.g. ``Smarter MCPServer``.
    verbose_name = f"{SMARTER_APP_NAME} {presentation_app_name}"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """
        Connect the app's signal receivers, once Django's apps are loaded.

        Importing :mod:`~smarter.apps.mcpserver.receivers` connects its ``@receiver`` functions
        to the signals of :mod:`~smarter.apps.mcpserver.signals`. The imports are inside this
        method because the receivers import the app's models, which cannot be imported until
        Django's apps are ready.
        """
        from . import receivers, signals  # noqa: F401

        app_title = f"{SMARTER_APP_NAME} {presentation_app_name}"
        logger.debug("%s app is %s", app_title, self.formatted_state_ready)
