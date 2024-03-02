# -*- coding: utf-8 -*-
"""WSGI config for smarter project."""
# wsgi.py
import logging
import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv
from whitenoise import WhiteNoise


BASE_DIR = Path(__file__).resolve().parent

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")

load_dotenv()
environment = os.getenv("ENVIRONMENT")
if environment == "prod":
    os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings.production"

static_root = BASE_DIR / "staticfiles"
application = get_wsgi_application()
application = WhiteNoise(application, root=static_root)

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info("WSGI config for smarter project.")
logger.info("Environment: %s", environment)
logger.info("WSGI application: %s", application)
logger.info("BASE_DIR: %s", BASE_DIR)
logger.info("DJANGO_SETTINGS_MODULE: %s", os.getenv("DJANGO_SETTINGS_MODULE"))
