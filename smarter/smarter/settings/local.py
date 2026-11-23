# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""
Django local settings for smarter project.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/6.0/ref/settings/
"""

import glob
import os
import sys
from typing import TYPE_CHECKING

from smarter.common.conf import smarter_settings
from smarter.common.utils.environment_settings import log_environment_settings
from smarter.lib.logging import getSmarterLogger

from .base import *
from .base import log_settings_diagnostics
from .overrides import apply_overrides

logger = getSmarterLogger(__name__)

if smarter_settings.developer_mode:
    # dev only:
    # Bootstrap theme source files and static assets.
    django_apps_dir = BASE_DIR / "apps"
    keen_source = [Path(p) for p in glob.glob(os.path.join(django_apps_dir, "*", "keen_demo1"))]
    STATICFILES_DIRS.extend(keen_source)
    # Uncompressed static files in development, unless they are on the CDN.
    if not smarter_settings.platform_static_files_on_cdn:
        STORAGES["staticfiles"] = {
            "BACKEND": "whitenoise.storage.StaticFilesStorage",
            "OPTIONS": {},
        }

    INSTALLED_APPS += ["django_extensions"]

ENVIRONMENT_DOMAIN = smarter_settings.environment_platform_domain
ENVIRONMENT_API_DOMAIN = smarter_settings.environment_api_domain

cors_ports = ["3000", "5173", "9357"]
for port in cors_ports:
    CORS_ALLOWED_ORIGINS.append(f"http://127.0.0.1:{port}")
    CORS_ALLOWED_ORIGINS.append(f"http://localhost:{port}")

CORS_ALLOWED_ORIGINS.append(f"http://{smarter_settings.environment_cdn_domain}")
CORS_ALLOWED_ORIGINS.append(f"https://{smarter_settings.environment_cdn_domain}")

CSRF_TRUSTED_ORIGINS = [f"http://{host}" for host in LOCAL_HOSTS]
CSRF_COOKIE_DOMAIN = ENVIRONMENT_DOMAIN.split(":")[0]
CSRF_COOKIE_SAMESITE = "lax"

# prevent browser caching in dev.
for template in TEMPLATES:
    if "OPTIONS" in template and "context_processors" in template["OPTIONS"]:
        template["OPTIONS"]["context_processors"].append("smarter.apps.dashboard.context_processors.cache_buster")

# Disable Django template caching in development environment.
TEMPLATES[0]["OPTIONS"]["debug"] = True

SMTP_SENDER = smarter_settings.subsystem_smtp_sender or ENVIRONMENT_DOMAIN
SMTP_FROM_EMAIL = smarter_settings.subsystem_smtp_from_email or "no-reply@" + SMTP_SENDER
SESSION_COOKIE_DOMAIN = ENVIRONMENT_DOMAIN.split(":")[0]
SESSION_COOKIE_SECURE = False
SESSION_COOKIE_SAMESITE = "lax"

environment_name = os.path.basename(__file__).replace(".py", "")
# The deployment's overrides overwrite every setting above: the overrides file, then
# DJANGO_* environment variables (the Helm chart's env on Kubernetes, .env locally). No setting is
# assigned below this line, and the settings are logged only below it, so that the log shows the
# values that Django runs with.
apply_overrides(globals())
log_settings_diagnostics(globals())

logger.debug("Loading smarter.settings.%s", environment_name)
if smarter_settings.platform_settings_output or "manage.py" not in sys.argv[0]:
    log_environment_settings(logger, smarter_settings, "PLATFORM")

# mypy can't evaluate a computed __all__, and would then treat a star import of this
# module as importing nothing. It skips this block, and exports every public name.
if not TYPE_CHECKING:
    __all__ = [
        name
        for name, value in globals().items()
        if name.isupper()
        and not name.startswith("_")
        and not hasattr(value, "__file__")
        and not callable(value)
        and value is not sys.modules[__name__]
    ]  # type: ignore[reportUnsupportedDunderAll]
