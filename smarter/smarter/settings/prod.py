# -*- coding: utf-8 -*-
# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""Django settings for platform.smarter.sh"""
import os

from .base_aws import *


environment_name = os.path.basename(__file__).replace(".py", "")
print(f"Loading smarter.settings.{environment_name}")

ENVIRONMENT_DOMAIN = f"platform.{SMARTER_ROOT_DOMAIN}"
ALLOWED_HOSTS = [ENVIRONMENT_DOMAIN]
SMTP_SENDER = os.environ.get("SMTP_SENDER", ENVIRONMENT_DOMAIN)
SMTP_FROM_EMAIL = os.environ.get("SMTP_FROM_EMAIL", "no-reply@" + SMTP_SENDER)

# (4_0.E001) As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme
# (usually http:// or https://) but found platform.smarter.sh. See the release notes for details.
CSRF_TRUSTED_ORIGINS = [f"http://{host}" for host in ALLOWED_HOSTS] + [f"https://{host}" for host in ALLOWED_HOSTS]
