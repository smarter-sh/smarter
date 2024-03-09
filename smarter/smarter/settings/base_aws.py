# -*- coding: utf-8 -*-
# pylint: disable=unused-wildcard-import,wildcard-import
"""Django base settings for environments deployed to AWS."""

import os

from .base import *


# SECURITY WARNING: keep the secret key used in production secret!
SECRET_KEY = os.getenv("SECRET_KEY")

# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = False

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("MYSQL_DATABASE"),
        "USER": os.getenv("MYSQL_USER"),
        "PASSWORD": os.getenv("MYSQL_PASSWORD"),
        "HOST": os.getenv("MYSQL_HOST"),
        "PORT": os.getenv("MYSQL_PORT", "3306"),  # default MySQL port
    }
}


STRIPE_LIVE_SECRET_KEY = os.environ.get("STRIPE_LIVE_SECRET_KEY", "<your secret key>")
STRIPE_TEST_SECRET_KEY = os.environ.get("STRIPE_TEST_SECRET_KEY", "<your secret key>")
STRIPE_LIVE_MODE = False  # Change to True in production
DJSTRIPE_WEBHOOK_SECRET = (
    "whsec_xxx"  # Get it from the section in the Stripe dashboard where you added the webhook endpoint
)
DJSTRIPE_USE_NATIVE_JSONFIELD = True  # We recommend setting to True for new installations
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# SMARTER settings
SMARTER_API_SCHEMA = "https"
