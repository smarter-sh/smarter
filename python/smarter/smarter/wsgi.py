# -*- coding: utf-8 -*-
"""
WSGI config for smarter project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application
from dotenv import load_dotenv


load_dotenv()
environment = os.getenv("ENVIRONMENT")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")

if environment == "production":
    os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings.production"

application = get_wsgi_application()
