# -*- coding: utf-8 -*-
# pylint: disable=unused-wildcard-import,wildcard-import
"""
Django local settings for smarter project.

For more information on this file, see
https://docs.djangoproject.com/en/5.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/5.0/ref/settings/
"""

import glob
import os

from .base import *


ENVIRONMENT_DOMAIN = "dev.platform.smarter.sh"

# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = "django-insecure-zp722j6hm29(=kro+i*)7p+f=@s)wlhj%8r!k#3qke(yb8%m_j"

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

if not DEBUG:
    ALLOWED_HOSTS = ["localhost", "127.0.0.1"]

# dev only:
# Bootstrap theme source files and static assets.
keen_source = glob.glob(os.path.join(django_apps_dir, "*", "keen_demo1"))
STATICFILES_DIRS.extend(keen_source)

INSTALLED_APPS += [
    "debug_toolbar",
    "django_extensions",
]

MIDDLEWARE += [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
]

CORS_ALLOWED_ORIGINS = [
    "http://localhost:5173",
]

# https://dj-stripe.dev/dj-stripe/2.7/installation/
STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<your secret key>")
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "<your secret key>")
STRIPE_LIVE_MODE = False  # Change to True in production
DJSTRIPE_WEBHOOK_SECRET = (
    "whsec_xxx"  # Get it from the section in the Stripe dashboard where you added the webhook endpoint
)
DJSTRIPE_USE_NATIVE_JSONFIELD = True  # We recommend setting to True for new installations
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

SMTP_SENDER = os.environ.get("SMTP_SENDER", ENVIRONMENT_DOMAIN)
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "no-reply@" + SMTP_SENDER)
