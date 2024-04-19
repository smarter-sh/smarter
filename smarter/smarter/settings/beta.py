# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""Django settings for beta.platform.smarter.sh"""
import os

from .base_docker import *


environment_name = os.path.basename(__file__).replace(".py", "")
print(f"Loading smarter.settings.{environment_name}")

if environment_name != SmarterEnvironments.BETA:
    raise SmarterConfigurationError(
        f"Iconsistent environment name: .env {environment_name} does not {SmarterEnvironments.BETA}"
    )

ENVIRONMENT_DOMAIN = f"{environment_name}.platform.{SMARTER_ROOT_DOMAIN}"
CUSTOMER_API_DOMAIN = smarter_settings.customer_api_domain
SMARTER_ALLOWED_HOSTS = [ENVIRONMENT_DOMAIN, CUSTOMER_API_DOMAIN, f"*.{CUSTOMER_API_DOMAIN}"]
SMTP_SENDER = smarter_settings.smtp_sender or ENVIRONMENT_DOMAIN
SMTP_FROM_EMAIL = smarter_settings.smtp_from_email or "no-reply@" + SMTP_SENDER

CORS_ALLOWED_ORIGINS = [f"https://{host}" for host in [ENVIRONMENT_DOMAIN, CUSTOMER_API_DOMAIN]]
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.beta\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.beta\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.beta\.api\.smarter\.sh$",
]

# (4_0.E001) As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme
# (usually http:// or https://) but found platform.smarter.sh. See the release notes for details.
CSRF_TRUSTED_ORIGINS = [f"http://{host}" for host in SMARTER_ALLOWED_HOSTS] + [
    f"https://{host}" for host in SMARTER_ALLOWED_HOSTS
]
CSRF_COOKIE_DOMAIN = ENVIRONMENT_DOMAIN
