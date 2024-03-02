# -*- coding: utf-8 -*-
"""WSGI config for smarter project."""
# wsgi.py
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

print(f"BASE_DIR: {BASE_DIR}")
print(f"Environment: {environment}")
print(f"Static root: {static_root}")
