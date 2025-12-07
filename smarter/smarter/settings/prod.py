# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""Django settings for platform.smarter.sh"""
import os

from .base_aws import *


environment_name = os.path.basename(__file__).replace(".py", "")
if environment_name != SmarterEnvironments.PROD:
    raise SmarterConfigurationError(
        f"Inconsistent environment name: .env {environment_name} does not {SmarterEnvironments.PROD}"
    )


CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.next\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.api\.smarter\.sh$",
]

# see: https://python-social-auth.readthedocs.io/en/latest/configuration/settings.html
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

logger.info("Loading smarter.settings.%s", environment_name)
if SMARTER_SETTINGS_OUTPUT or "manage.py" not in sys.argv[0]:

    logger.info("*" * 80)
    logger.info("CORS_ALLOWED_ORIGINS: %s", CORS_ALLOWED_ORIGINS)
    logger.info("CORS_ALLOWED_ORIGIN_REGEXES: %s", CORS_ALLOWED_ORIGIN_REGEXES)
    logger.info("ENVIRONMENT_API_DOMAIN: %s", ENVIRONMENT_API_DOMAIN)
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
    if not SESSION_COOKIE_SECURE:
        logger.warning(
            "WARNING: SESSION_COOKIE_SECURE should be set to True. The current setting makes the cookie vulnerable to man-in-the-middle attacks."
        )
        logger.info("*" * 80)
