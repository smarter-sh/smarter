# pylint: disable=E0402,unused-wildcard-import,wildcard-import
"""Django base settings for environments deployed to AWS."""

import logging
import os
import sys

from smarter.common.conf import smarter_settings

from .base import *


logger = logging.getLogger(__name__)
logger.info("Loading smarter.settings.base_aws")

CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": os.getenv(
            "CACHES_LOCATION",
            f"redis://:smarter@smarter-redis-master.smarter-platform-{smarter_settings.environment}.svc.cluster.local:6379/1",
        ),
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
        },
    }
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"

# Celery Configuration
CELERY_BROKER_URL = os.getenv(
    "CELERY_BROKER_URL",
    f"redis://:smarter@smarter-redis-master.smarter-platform-{smarter_settings.environment}.svc.cluster.local:6379/1",
)
CELERY_REDBEAT_REDIS_URL = CELERY_BROKER_URL
CELERY_BEAT_SCHEDULER = "redbeat.RedBeatScheduler"

# Database
# https://docs.djangoproject.com/en/5.0/ref/settings/#databases

DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.mysql",
        "NAME": os.getenv("SMARTER_MYSQL_DATABASE"),
        "USER": os.getenv("SMARTER_MYSQL_USER"),
        "PASSWORD": os.getenv("SMARTER_MYSQL_PASSWORD"),
        "HOST": os.getenv("SMARTER_MYSQL_HOST"),
        "PORT": os.getenv("SMARTER_MYSQL_PORT", "3306"),  # default MySQL port
    }
}


STRIPE_LIVE_SECRET_KEY = (
    smarter_settings.stripe_live_secret_key.get_secret_value() if smarter_settings.stripe_live_secret_key else ""
)
STRIPE_TEST_SECRET_KEY = (
    smarter_settings.stripe_test_secret_key.get_secret_value() if smarter_settings.stripe_test_secret_key else ""
)
STRIPE_LIVE_MODE = False  # Change to True in production
DJSTRIPE_WEBHOOK_SECRET = (
    "whsec_xxx"  # Get it from the section in the Stripe dashboard where you added the webhook endpoint
)
DJSTRIPE_USE_NATIVE_JSONFIELD = True  # We recommend setting to True for new installations
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

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

ENVIRONMENT_DOMAIN = smarter_settings.environment_platform_domain
ENVIRONMENT_API_DOMAIN = smarter_settings.environment_api_domain
SMTP_SENDER = smarter_settings.smtp_sender or ENVIRONMENT_DOMAIN
SMTP_FROM_EMAIL = smarter_settings.smtp_from_email or "no-reply@" + SMTP_SENDER

CORS_ALLOWED_ORIGINS += [
    f"http://{host}" for host in [ENVIRONMENT_DOMAIN, ENVIRONMENT_API_DOMAIN, smarter_settings.environment_cdn_domain]
]
CORS_ALLOWED_ORIGINS += [
    f"https://{host}" for host in [ENVIRONMENT_DOMAIN, ENVIRONMENT_API_DOMAIN, smarter_settings.environment_cdn_domain]
]


# (4_0.E001) As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme
# (usually http:// or https://) but found platform.smarter.sh. See the release notes for details.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in smarter_settings.allowed_hosts]

__all__ = [
    name
    for name, value in globals().items()
    if name.isupper()
    and not name.startswith("_")
    and not hasattr(value, "__file__")
    and not callable(value)
    and value is not sys.modules[__name__]
]  # type: ignore[reportUnsupportedDunderAll]
