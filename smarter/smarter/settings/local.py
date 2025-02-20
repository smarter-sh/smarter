# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
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


logger.info("Loading smarter.settings.local")

ENVIRONMENT_DOMAIN = smarter_settings.environment_domain
CUSTOMER_API_DOMAIN = smarter_settings.customer_api_domain

SMARTER_ALLOWED_HOSTS = LOCAL_HOSTS

# dev only:
# Bootstrap theme source files and static assets.
keen_source = glob.glob(os.path.join(django_apps_dir, "*", "keen_demo1"))
STATICFILES_DIRS.extend(keen_source)
STATICFILES_STORAGE = "whitenoise.storage.StaticFilesStorage"

INSTALLED_APPS += ["django_extensions"]

# if DEBUG and not "test" in sys.argv:
#     INSTALLED_APPS += [
#         "debug_toolbar",
#     ]

#     MIDDLEWARE += [
#         "debug_toolbar.middleware.DebugToolbarMiddleware",
#     ]

MIDDLEWARE += [
    "corsheaders.middleware.CorsMiddleware",
]
CORS_ALLOWED_ORIGINS += [
    "http://127.0.0.1:5173",  # Django
    "http://127.0.0.1:3000",  # React
    "http://127.0.0.1:8000",  # Django
    "http://localhost:5173",
    "http://localhost:8000",
    "http://localhost:3000",
]
CORS_ALLOWED_ORIGINS.append(f"http://{smarter_settings.environment_cdn_domain}")
CORS_ALLOWED_ORIGINS.append(f"https://{smarter_settings.environment_cdn_domain}")

CSRF_TRUSTED_ORIGINS = [f"http://{host}" for host in smarter_settings.local_hosts]
CSRF_COOKIE_DOMAIN = ENVIRONMENT_DOMAIN.split(":")[0]
CSRF_COOKIE_SAMESITE = "lax"

# prevent browser caching in dev.
for template in TEMPLATES:
    if "OPTIONS" in template and "context_processors" in template["OPTIONS"]:
        template["OPTIONS"]["context_processors"].append("smarter.apps.dashboard.context_processors.cache_buster")

# https://dj-stripe.dev/dj-stripe/2.7/installation/
STRIPE_LIVE_SECRET_KEY = smarter_settings.stripe_live_secret_key
STRIPE_TEST_SECRET_KEY = smarter_settings.stripe_test_secret_key
STRIPE_LIVE_MODE = False  # Change to True in production
DJSTRIPE_WEBHOOK_SECRET = (
    "whsec_xxx"  # Get it from the section in the Stripe dashboard where you added the webhook endpoint
)
DJSTRIPE_USE_NATIVE_JSONFIELD = True  # We recommend setting to True for new installations
DJSTRIPE_FOREIGN_KEY_TO_FIELD = "id"

# Disable Django template caching in development environment.
TEMPLATES[0]["OPTIONS"]["debug"] = True

SMTP_SENDER = smarter_settings.smtp_sender or ENVIRONMENT_DOMAIN
SMTP_FROM_EMAIL = smarter_settings.smtp_from_email or "no-reply@" + SMTP_SENDER
SESSION_COOKIE_DOMAIN = ENVIRONMENT_DOMAIN.split(":")[0]
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "lax"

logger.info("*" * 80)
logger.info("CORS_ALLOW_HEADERS: %s", CORS_ALLOW_HEADERS)
logger.info("CORS_ALLOWED_ORIGINS: %s", CORS_ALLOWED_ORIGINS)
logger.info("CORS_ALLOWED_ORIGIN_REGEXES: %s", CORS_ALLOWED_ORIGIN_REGEXES)
logger.info("CUSTOMER_API_DOMAIN: %s", CUSTOMER_API_DOMAIN)
logger.info("ENVIRONMENT_DOMAIN: %s", ENVIRONMENT_DOMAIN)
logger.info("SECURE_PROXY_SSL_HEADER: %s", SECURE_PROXY_SSL_HEADER)
logger.info("SMARTER_API_SCHEMA: %s", SMARTER_API_SCHEMA)
logger.info("SMARTER_ALLOWED_HOSTS: %s", SMARTER_ALLOWED_HOSTS)
logger.info("SMTP_SENDER: %s", SMTP_SENDER)
logger.info("SMTP_FROM_EMAIL: %s", SMTP_FROM_EMAIL)
logger.info("-" * 80)
logger.info("CSRF_COOKIE_DOMAIN: %s", CSRF_COOKIE_DOMAIN)
logger.info("CSRF_COOKIE_SAMESITE: %s", CSRF_COOKIE_SAMESITE)
logger.info("CSRF_COOKIE_SECURE: %s", CSRF_COOKIE_SECURE)
logger.info("CSRF_TRUSTED_ORIGINS: %s", CSRF_TRUSTED_ORIGINS)
logger.info("-" * 80)
logger.info("SESSION_COOKIE_DOMAIN: %s", SESSION_COOKIE_DOMAIN)
logger.info("SESSION_COOKIE_SAMESITE: %s", SESSION_COOKIE_SAMESITE)
logger.info("SESSION_COOKIE_SECURE: %s", SESSION_COOKIE_SECURE)
logger.info("SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI: %s", SOCIAL_AUTH_GOOGLE_OAUTH2_REDIRECT_URI)
logger.info("SOCIAL_AUTH_LINKEDIN_OAUTH2_REDIRECT_URI: %s", SOCIAL_AUTH_LINKEDIN_OAUTH2_REDIRECT_URI)
logger.info("*" * 80)
