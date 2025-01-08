# pylint: disable=E0402,unused-wildcard-import,wildcard-import
"""Django base settings for environments deployed to AWS."""

import os

from .base import *


CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv(
            "CACHES_LOCATION", "redis://:smarter@smarter-redis-master.smarter-platform-dev.svc.cluster.local:6379/1"
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Celery Configuration
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL", "redis://:smarter@smarter-redis-master.smarter-platform-dev.svc.cluster.local:6379/1"
)
CELERY_REDBEAT_REDIS_URL = CELERY_BROKER_URL
CELERY_BEAT_SCHEDULER = "redbeat.RedBeatScheduler"

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


STRIPE_LIVE_SECRET_KEY = smarter_settings.stripe_live_secret_key
STRIPE_TEST_SECRET_KEY = smarter_settings.stripe_test_secret_key
STRIPE_LIVE_MODE = False  # Change to True in production
DJSTRIPE_WEBHOOK_SECRET = (
    "whsec_xxx"  # Get it from the section in the Stripe dashboard where you added the webhook endpoint
)
DJSTRIPE_USE_NATIVE_JSONFIELD = True  # We recommend setting to True for new installations
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# SMARTER settings
SMARTER_API_SCHEMA = "https"

# Common security settings
# SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
SECURE_PROXY_SSL_HEADER = None

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.api\.smarter\.sh$",
]
# settings that affect whether the browser saves cookies
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True

ENVIRONMENT_DOMAIN = smarter_settings.environment_domain
CUSTOMER_API_DOMAIN = smarter_settings.customer_api_domain
SMARTER_ALLOWED_HOSTS = [ENVIRONMENT_DOMAIN, CUSTOMER_API_DOMAIN, f"*.{CUSTOMER_API_DOMAIN}"]
SMTP_SENDER = smarter_settings.smtp_sender or ENVIRONMENT_DOMAIN
SMTP_FROM_EMAIL = smarter_settings.smtp_from_email or "no-reply@" + SMTP_SENDER

CORS_ALLOWED_ORIGINS = [f"https://{host}" for host in [ENVIRONMENT_DOMAIN, CUSTOMER_API_DOMAIN]]

# (4_0.E001) As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme
# (usually http:// or https://) but found platform.smarter.sh. See the release notes for details.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in SMARTER_ALLOWED_HOSTS]
