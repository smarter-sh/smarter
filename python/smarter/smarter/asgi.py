# -*- coding: utf-8 -*-
"""
ASGI config for smarter project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/howto/deployment/asgi/
"""

import os

from django.core.asgi import get_asgi_application
from dotenv import load_dotenv


load_dotenv()
environment = os.getenv("ENVIRONMENT")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "smarter.settings.local")

if environment == "production":
    os.environ["DJANGO_SETTINGS_MODULE"] = "smarter.settings.production"

application = get_asgi_application()
