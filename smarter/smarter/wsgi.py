# -*- coding: utf-8 -*-
"""WSGI config for smarter project."""
# wsgi.py
import os
from pathlib import Path

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv
from whitenoise import WhiteNoise


BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv()
environment = os.getenv("ENVIRONMENT")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")

application = get_wsgi_application()

if environment == "prod":
    os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings.production"
    application = WhiteNoise(application, root="/app/staticfiles")
else:
    application = WhiteNoise(application, root=os.path.join(BASE_DIR, "staticfiles"))
