# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""Django settings for alpha.platform.smarter.sh"""
import os

from .base_aws import *


environment_name = os.path.basename(__file__).replace(".py", "")
print(f"Loading smarter.settings.{environment_name}")

if environment_name != SmarterEnvironments.ALPHA:
    raise SmarterConfigurationError(
        f"Iconsistent environment name: .env {environment_name} does not {SmarterEnvironments.ALPHA}"
    )

ENVIRONMENT_DOMAIN = f"{environment_name}.platform.{SMARTER_ROOT_DOMAIN}"
CUSTOMER_API_DOMAIN = smarter_settings.customer_api_domain
SMARTER_ALLOWED_HOSTS = [ENVIRONMENT_DOMAIN, CUSTOMER_API_DOMAIN, f"*.{CUSTOMER_API_DOMAIN}"]
SMTP_SENDER = smarter_settings.smtp_sender or ENVIRONMENT_DOMAIN
SMTP_FROM_EMAIL = smarter_settings.smtp_from_email or "no-reply@" + SMTP_SENDER

CORS_ALLOWED_ORIGINS = [f"https://{host}" for host in [ENVIRONMENT_DOMAIN, CUSTOMER_API_DOMAIN]]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.alpha\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.alpha\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.alpha\.api\.smarter\.sh$",
]

# (4_0.E001) As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme
# (usually http:// or https://) but found platform.smarter.sh. See the release notes for details.
CSRF_TRUSTED_ORIGINS = [f"https://{host}" for host in SMARTER_ALLOWED_HOSTS]
CSRF_COOKIE_DOMAIN = ENVIRONMENT_DOMAIN

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
logger.info("SESSION_COOKIE_SECURE: %s", SESSION_COOKIE_SECURE)
logger.info("SESSION_COOKIE_SAMESITE: %s", SESSION_COOKIE_SAMESITE)
logger.info("*" * 80)
