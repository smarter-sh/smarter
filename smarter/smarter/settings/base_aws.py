# pylint: disable=E0402,unused-wildcard-import,wildcard-import
"""Django base settings for environments deployed to AWS."""

import sys
from typing import TYPE_CHECKING

from smarter.common.conf import smarter_settings
from smarter.common.utils.redis_url import redis_server_url, redis_url_with_database
from smarter.lib import json
from smarter.lib.logging import getSmarterLogger

from .base import *

logger = getSmarterLogger(__name__)
logger.debug("Loading smarter.settings.base_aws")
# Redis's password is generated per environment by smarter-infrastructure (the Kubernetes Secret
# smarter-redis-password), never a default: it guards the Celery queues, whose workers hold the
# platform's credentials, and every user's session (ADR-030, rule 5). The tool worker authenticates
# as its own ACL user, tools, with that user's password (rule 8).
redis_host = (
    f"{smarter_settings.platform_shared_resource_identifier}-redis-master."
    f"{smarter_settings.environment_namespace}.svc.cluster.local:6379"
)
default_redis_server = redis_server_url(
    redis_host,
    smarter_settings.subsystem_redis_username,
    smarter_settings.require_redis_password().get_secret_value(),
)
# The cache and the Celery broker use different Redis databases, so that cache.clear()
# can't delete the Celery queues. See CELERY_BROKER_URL in base.py.
default_redis_location = f"{default_redis_server}/1"
default_broker_location = f"{default_redis_server}/0"

# The chart's own Redis. For another, set DJANGO_CACHES, with both caches, and DJANGO_CELERY_BROKER_URL
# (see smarter.settings.overrides).
cache_location = default_redis_location
CACHES = {
    "default": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": cache_location,
        # See CACHE_KEY_PREFIX in base.py.
        "KEY_PREFIX": CACHE_KEY_PREFIX,
        "OPTIONS": CACHE_OPTIONS,
    },
    # Sessions are in their own database of the same server, so that cache.clear() doesn't
    # log users out. See SESSION_CACHE_ALIAS in base.py.
    "sessions": {
        "BACKEND": "django_redis.cache.RedisCache",
        "LOCATION": redis_url_with_database(cache_location, 2),
        "OPTIONS": CACHE_OPTIONS,
    },
}

SESSION_ENGINE = "django.contrib.sessions.backends.cache"
SESSION_CACHE_ALIAS = "sessions"

# Celery Configuration
CELERY_BROKER_URL = default_broker_location
# A DJANGO_CELERY_BROKER_URL override moves this too: see DERIVED_SETTINGS in smarter.settings.overrides.
CELERY_REDBEAT_REDIS_URL = CELERY_BROKER_URL
CELERY_BEAT_SCHEDULER = "redbeat.RedBeatScheduler"

# Database: DATABASES is base.py's, from smarter_settings.sql_*.

# Common security settings
# Traefik terminates TLS and forwards plain HTTP, with X-Forwarded-Proto set to the scheme the browser
# used. It overwrites the header of a request from outside the VPC, so a client can't forge it. With
# this, request.is_secure() and build_absolute_uri() reflect the browser's https.
SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.api\.smarter\.sh$",
]
# settings that affect whether the browser saves cookies. Every ingress serves HTTPS only, so the
# browser always has a secure context for both cookies.
CSRF_COOKIE_SECURE = True
CSRF_COOKIE_SAMESITE = "Lax"

SESSION_COOKIE_SECURE = True
SESSION_COOKIE_SAMESITE = "Lax"
SESSION_COOKIE_HTTPONLY = True

ENVIRONMENT_DOMAIN = smarter_settings.environment_platform_domain
ENVIRONMENT_API_DOMAIN = smarter_settings.environment_api_domain
SMTP_SENDER = smarter_settings.subsystem_smtp_sender or ENVIRONMENT_DOMAIN
SMTP_FROM_EMAIL = smarter_settings.subsystem_smtp_from_email or "no-reply@" + SMTP_SENDER

CORS_ALLOWED_ORIGINS += [
    f"http://{host}" for host in [ENVIRONMENT_DOMAIN, ENVIRONMENT_API_DOMAIN, smarter_settings.environment_cdn_domain]
]
CORS_ALLOWED_ORIGINS += [
    f"https://{host}" for host in [ENVIRONMENT_DOMAIN, ENVIRONMENT_API_DOMAIN, smarter_settings.environment_cdn_domain]
]


# (4_0.E001) As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme
# (usually http:// or https://) but found platform.smarter.sh. See the release notes for details.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in smarter_settings.allowed_hosts]

if smarter_settings.platform_settings_output or "manage.py" not in sys.argv[0]:
    cache_backend = CACHES.get("default", {}).get("BACKEND", "not configured")
    logger.debug("Cache backend: %s", json.dumps(CACHES))
    if cache_backend != "django_redis.cache.RedisCache":
        logger.warning("Recommended cache backend is django_redis.cache.RedisCache")


# mypy can't evaluate a computed __all__, and would then treat a star import of this
# module as importing nothing. It skips this block, and exports every public name.
if not TYPE_CHECKING:
    __all__ = [
        name
        for name, value in globals().items()
        if name.isupper()
        and not name.startswith("_")
        and not hasattr(value, "__file__")
        and not callable(value)
        and value is not sys.modules[__name__]
    ]  # type: ignore[reportUnsupportedDunderAll]
