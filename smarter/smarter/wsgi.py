"""WSGI config for smarter project."""

# wsgi.py
import logging
import os

from django.conf import settings
from django.core.wsgi import get_wsgi_application
from whitenoise import WhiteNoise

from smarter.common.conf import settings as smarter_settings


os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings." + smarter_settings.environment

application = get_wsgi_application()
application = WhiteNoise(application, root=settings.STATIC_ROOT)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
logger.debug("WSGI config for smarter.")
logger.debug("WSGI application: %s", application)
logger.debug("DJANGO_SETTINGS_MODULE: %s", os.getenv("DJANGO_SETTINGS_MODULE"))
logger.debug("static_root: %s", settings.STATIC_ROOT)

__all__ = ["application"]
