# -*- coding: utf-8 -*-
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
logger.info("WSGI config for smarter.")
logger.info("WSGI application: %s", application)
logger.info("DJANGO_SETTINGS_MODULE: %s", os.getenv("DJANGO_SETTINGS_MODULE"))
logger.info("static_root: %s", settings.STATIC_ROOT)
