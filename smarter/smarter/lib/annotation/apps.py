"""Django app configuration of Smarter annotations."""

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .const import namespace as app_name

logger = logging.getSmarterLogger(__name__)


class AnnotationConfig(AppConfig):
    """Django app configuration of Smarter annotations."""

    name = "smarter.lib.annotation"
    label = "annotation"
    verbose_name = f"{SMARTER_APP_NAME} {app_name.capitalize()}"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Connect the receivers."""
        from . import receivers  # noqa: F401

        app_label = f"{SMARTER_APP_NAME} {app_name.capitalize()}"
        logger.debug("%s app is %s", app_label, SmarterReadyState.READY)
