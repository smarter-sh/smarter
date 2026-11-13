"""Django app configuration of Smarter annotations."""

from django.apps import AppConfig

from smarter.common.const import SMARTER_APP_NAME
from smarter.common.mixins.helper_mixin import SmarterReadyState
from smarter.lib import logging

from .const import namespace as app_name

logger = logging.getSmarterLogger(__name__)
logger_prefix = logging.SmarterFormattedText.text(__name__)


class AnnotationConfig(AppConfig):
    """Django app configuration of Smarter annotations."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "smarter.lib.annotation"
    label = "annotation"
    verbose_name = f"{SMARTER_APP_NAME} {app_name.capitalize()}"

    # pylint: disable=import-outside-toplevel,W0611
    def ready(self):
        """Connect the receivers."""
        from . import receivers  # noqa: F401

        app_label = f"{SMARTER_APP_NAME} {app_name.capitalize()}"
        logger.debug("%s.ready() %s app is %s", logger_prefix, app_label, SmarterReadyState.READY)
