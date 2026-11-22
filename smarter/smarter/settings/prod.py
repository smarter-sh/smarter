# pylint: disable=E0402,E0602,unused-wildcard-import,wildcard-import
"""Django settings for platform.smarter.sh."""

import os
import sys
from typing import TYPE_CHECKING

from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.common.exceptions import SmarterConfigurationError
from smarter.common.utils.environment_settings import log_environment_settings
from smarter.lib.logging import getSmarterLogger

from .base import log_settings_diagnostics
from .base_aws import *
from .overrides import apply_overrides

logger = getSmarterLogger(__name__)


environment_name = os.path.basename(__file__).replace(".py", "")
if environment_name != SmarterEnvironments.PROD:
    raise SmarterConfigurationError(
        f"Inconsistent environment name: .env {environment_name} does not {SmarterEnvironments.PROD}"
    )


CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^https?://[\w-]+\.(\d+-\d+-\d+)\.api\.smarter\.sh$",
    r"^https?://[\w-]+\.platform\.smarter\.sh$",
    r"^https?://[\w-]+\.api\.smarter\.sh$",
]

# see: https://python-social-auth.readthedocs.io/en/latest/configuration/settings.html
SOCIAL_AUTH_REDIRECT_IS_HTTPS = True

# The deployment's overrides overwrite every setting above: the overrides file, then
# DJANGO_* environment variables (the Helm chart's env on Kubernetes, .env locally). No setting is
# assigned below this line, and the settings are logged only below it, so that the log shows the
# values that Django runs with.
apply_overrides(globals())
log_settings_diagnostics(globals())

logger.debug("Loading smarter.settings.%s", environment_name)
if smarter_settings.platform_settings_output or "manage.py" not in sys.argv[0]:
    log_environment_settings(logger, smarter_settings, "PLATFORM")
    if not SESSION_COOKIE_SECURE:
        logger.warning(
            "SESSION_COOKIE_SECURE should be set to True. The current setting makes the cookie vulnerable to man-in-the-middle attacks."
        )

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
