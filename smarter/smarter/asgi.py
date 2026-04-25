"""
ASGI config for smarter project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import logging
import os

from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.conf import settings
from django.contrib.staticfiles.handlers import ASGIStaticFilesHandler
from django.core.asgi import get_asgi_application

from smarter.apps.prompt.routing import websocket_urlpatterns
from smarter.common.conf import smarter_settings

os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings." + smarter_settings.environment


django_asgi_app = get_asgi_application()
django_asgi_app = ASGIStaticFilesHandler(django_asgi_app)


application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(URLRouter(websocket_urlpatterns)),
    }
)

logger = logging.getLogger(__name__)
logger.debug("ASGI config for smarter.")
logger.debug("ASGI application: %s", application)
logger.debug("DJANGO_SETTINGS_MODULE: %s", os.getenv("DJANGO_SETTINGS_MODULE"))
logger.debug("static_root: %s", settings.STATIC_ROOT)

__all__ = ["application"]
