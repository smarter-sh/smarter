# -*- coding: utf-8 -*-
# pylint: disable=unused-wildcard-import,wildcard-import
"""Django settings for staging.platform.smarter.sh"""

from .base_aws import *


ENVIRONMENT_DOMAIN = "staging.platform.smarter.sh"

ALLOWED_HOSTS = [ENVIRONMENT_DOMAIN]

# (4_0.E001) As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme
# (usually http:// or https://) but found platform.smarter.sh. See the release notes for details.
CSRF_TRUSTED_ORIGINS = [f"http://{host}" for host in ALLOWED_HOSTS] + [f"https://{host}" for host in ALLOWED_HOSTS]

SMTP_SENDER = os.environ.get("SMTP_SENDER", ENVIRONMENT_DOMAIN)
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "no-reply@" + SMTP_SENDER)
