"""Smarter API Plugin Manifest"""

import logging
from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys

from .const import MANIFEST_KIND
from .spec import SAMPluginStaticSpec


MODULE_IDENTIFIER = MANIFEST_KIND


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMStaticPlugin(SAMPluginCommon):
    """Smarter API Manifest - Plugin"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMPluginStaticSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
