# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""Django settings for beta.platform.smarter.sh"""
import os

from .base_aws import *


environment_name = os.path.basename(__file__).replace(".py", "")
print(f"Loading smarter.settings.{environment_name}")

if environment_name != SmarterEnvironments.BETA:
    raise SmarterConfigurationError(
        f"Iconsistent environment name: .env {environment_name} does not {SmarterEnvironments.BETA}"
    )

CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.beta\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.beta\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.beta\.api\.smarter\.sh$",
]


logger.info("*" * 80)
logger.info("ENVIRONMENT_DOMAIN: %s", ENVIRONMENT_DOMAIN)
logger.info("CUSTOMER_API_DOMAIN: %s", CUSTOMER_API_DOMAIN)
logger.info("SMTP_SENDER: %s", SMTP_SENDER)
logger.info("SMTP_FROM_EMAIL: %s", SMTP_FROM_EMAIL)
logger.info("SMARTER_API_SCHEMA: %s", SMARTER_API_SCHEMA)
logger.info("SECURE_PROXY_SSL_HEADER: %s", SECURE_PROXY_SSL_HEADER)
logger.info("SMARTER_ALLOWED_HOSTS: %s", SMARTER_ALLOWED_HOSTS)
logger.info("CORS_ALLOWED_ORIGINS: %s", CORS_ALLOWED_ORIGINS)
logger.info("CORS_ALLOWED_ORIGIN_REGEXES: %s", CORS_ALLOWED_ORIGIN_REGEXES)
logger.info("CSRF_COOKIE_DOMAIN: %s", CSRF_COOKIE_DOMAIN)
logger.info("CSRF_COOKIE_SAMESITE: %s", CSRF_COOKIE_SAMESITE)
logger.info("CSRF_COOKIE_SECURE: %s", CSRF_COOKIE_SECURE)
logger.info("CSRF_TRUSTED_ORIGINS: %s", CSRF_TRUSTED_ORIGINS)
logger.info("SESSION_COOKIE_DOMAIN: %s", SESSION_COOKIE_DOMAIN)
logger.info("SESSION_COOKIE_SECURE: %s", SESSION_COOKIE_SECURE)
logger.info("SESSION_COOKIE_SAMESITE: %s", SESSION_COOKIE_SAMESITE)
logger.info("*" * 80)
if not SESSION_COOKIE_SECURE:
    logger.warning(
        "WARNING: SESSION_COOKIE_SECURE should be set to True. The current setting makes the cookie vulnerable to man-in-the-middle attacks."
    )
    logger.info("*" * 80)
