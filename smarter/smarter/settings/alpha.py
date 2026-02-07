# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""Django settings for alpha.platform.smarter.sh"""

import logging
import os
import sys

from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError

from .base_aws import *

logger = logging.getLogger(__name__)


environment_name = os.path.basename(__file__).replace(".py", "")
if environment_name != SmarterEnvironments.ALPHA:
    raise SmarterConfigurationError(
        f"Inconsistent environment name: .env {environment_name} does not {SmarterEnvironments.ALPHA}"
    )

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.alpha\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.alpha\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.alpha\.api\.smarter\.sh$",
]
# for react.js local dev/test
CORS_ALLOWED_ORIGINS += [
    "http://127.0.0.1:3000",
    "http://localhost:3000",
]

# see: https://python-social-auth.readthedocs.io/en/latest/configuration/settings.html
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

logger.debug("Loading smarter.settings.%s", environment_name)
if smarter_settings.settings_output or "manage.py" not in sys.argv[0]:

    logger.debug("*" * 80)
    logger.debug("CORS_ALLOWED_ORIGINS: %s", CORS_ALLOWED_ORIGINS)
    logger.debug("CORS_ALLOWED_ORIGIN_REGEXES: %s", CORS_ALLOWED_ORIGIN_REGEXES)
    logger.debug("ENVIRONMENT_API_DOMAIN: %s", ENVIRONMENT_API_DOMAIN)
    logger.debug("ENVIRONMENT_DOMAIN: %s", ENVIRONMENT_DOMAIN)
    logger.debug("SECURE_PROXY_SSL_HEADER: %s", SECURE_PROXY_SSL_HEADER)
    logger.debug("API_SCHEMA: %s", smarter_settings.api_schema)
    logger.debug("ALLOWED_HOSTS: %s", smarter_settings.allowed_hosts)
    logger.debug("SMTP_SENDER: %s", SMTP_SENDER)
    logger.debug("SMTP_FROM_EMAIL: %s", SMTP_FROM_EMAIL)
    logger.debug("-" * 80)
    logger.debug("CSRF_COOKIE_DOMAIN: %s", CSRF_COOKIE_DOMAIN)
    logger.debug("CSRF_COOKIE_SAMESITE: %s", CSRF_COOKIE_SAMESITE)
    logger.debug("CSRF_COOKIE_SECURE: %s", CSRF_COOKIE_SECURE)
    logger.debug("CSRF_TRUSTED_ORIGINS: %s", CSRF_TRUSTED_ORIGINS)
    logger.debug("-" * 80)
    logger.debug("SESSION_COOKIE_DOMAIN: %s", SESSION_COOKIE_DOMAIN)
    logger.debug("SESSION_COOKIE_SAMESITE: %s", SESSION_COOKIE_SAMESITE)
    logger.debug("SESSION_COOKIE_SECURE: %s", SESSION_COOKIE_SECURE)
    logger.debug("*" * 80)
    if not SESSION_COOKIE_SECURE:
        logger.warning(
            "WARNING: SESSION_COOKIE_SECURE should be set to True. The current setting makes the cookie vulnerable to man-in-the-middle attacks."
        )
        logger.debug("*" * 80)

__all__ = [
    name
    for name, value in globals().items()
    if name.isupper()
    and not name.startswith("_")
    and not hasattr(value, "__file__")
    and not callable(value)
    and value is not sys.modules[__name__]
]  # type: ignore[reportUnsupportedDunderAll]
