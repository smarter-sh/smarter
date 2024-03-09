# -*- coding: utf-8 -*-
# pylint: disable=unused-wildcard-import,wildcard-import
"""Django settings for dev.platform.smarter.sh"""

from .base_aws import *


ALLOWED_HOSTS = ["dev.platform.smarter.sh"]

# (4_0.E001) As of Django 4.0, the values in the CSRF_TRUSTED_ORIGINS setting must start with a scheme
# (usually http:// or https://) but found platform.smarter.sh. See the release notes for details.
CSRF_TRUSTED_ORIGINS = [f"http://{host}" for host in ALLOWED_HOSTS] + [f"https://{host}" for host in ALLOWED_HOSTS]
