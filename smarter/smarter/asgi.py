"""
ASGI config for smarter project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

from smarter.common.conf import smarter_settings
from smarter.common.helpers.startup_banner import print_startup_banner
from smarter.lib import logging
from smarter.lib.django.healthz import HealthzASGIMiddleware

os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings." + smarter_settings.environment


# Django must be set up, with its app registry populated, before anything imports a model, so
# the WebSocket consumers, whose modules do, are imported after this. See the Channels docs.
django_asgi_app = get_asgi_application()
static_asgi_app = ASGIStaticFilesHandler(django_asgi_app)

from smarter import consumers  # noqa: E402  pylint: disable=wrong-import-position

websocket_application = AllowedHostsOriginValidator(AuthMiddlewareStack(URLRouter(consumers.urlpatterns)))


# the liveness probe, /healthz/, is answered before Django, so that it says whether the process is
# alive, not whether its middleware's Redis and database are. See smarter.lib.django.healthz.
application = HealthzASGIMiddleware(
    ProtocolTypeRouter(
        {
            "http": static_asgi_app,
            "websocket": websocket_application,
        }
    )
)

logger = logging.getLogger(__name__)
logger.debug("smarter is using django.core.asgi with ASGIStaticFilesHandler for static files.")
logger.debug("ASGI application: %s", application)
logger.debug("static_root: %s", settings.STATIC_ROOT)
logger.debug("DJANGO_SETTINGS_MODULE: %s", os.getenv("DJANGO_SETTINGS_MODULE"))

print_startup_banner()

__all__ = ["application"]
