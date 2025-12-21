# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""Django settings for next.platform.smarter.sh"""
import logging
import os
import sys

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError

from .base_aws import *


logger = logging.getLogger(__name__)


environment_name = os.path.basename(__file__).replace(".py", "")
if environment_name != SmarterEnvironments.NEXT:
    raise SmarterConfigurationError(
        f"Inconsistent environment name: .env {environment_name} does not {SmarterEnvironments.NEXT}"
    )


CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.next\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.next\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.next\.api\.smarter\.sh$",
]

# see: https://python-social-auth.readthedocs.io/en/latest/configuration/settings.html
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

logger.info("Loading smarter.settings.%s", environment_name)
if smarter_settings.settings_output or "manage.py" not in sys.argv[0]:

    logger.info("*" * 80)
    logger.info("CORS_ALLOWED_ORIGINS: %s", CORS_ALLOWED_ORIGINS)
    logger.info("CORS_ALLOWED_ORIGIN_REGEXES: %s", CORS_ALLOWED_ORIGIN_REGEXES)
    logger.info("ENVIRONMENT_API_DOMAIN: %s", ENVIRONMENT_API_DOMAIN)
    logger.info("ENVIRONMENT_DOMAIN: %s", ENVIRONMENT_DOMAIN)
    logger.info("SECURE_PROXY_SSL_HEADER: %s", SECURE_PROXY_SSL_HEADER)
    logger.info("API_SCHEMA: %s", smarter_settings.api_schema)
    logger.info("ALLOWED_HOSTS: %s", smarter_settings.allowed_hosts)
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
    logger.info("*" * 80)
    if not SESSION_COOKIE_SECURE:
        logger.warning(
            "WARNING: SESSION_COOKIE_SECURE should be set to True. The current setting makes the cookie vulnerable to man-in-the-middle attacks."
        )
        logger.info("*" * 80)

__all__ = [
    name
    for name, value in globals().items()
    if name.isupper()
    and not name.startswith("_")
    and not hasattr(value, "__file__")
    and not callable(value)
    and value is not sys.modules[__name__]
]  # type: ignore[reportUnsupportedDunderAll]
