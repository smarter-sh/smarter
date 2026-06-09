"""Smarter API Plugin Manifest"""

from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.enum import SAMKeys

from .const import MANIFEST_KIND
from .spec import SAMPluginStaticSpec

MODULE_IDENTIFIER = MANIFEST_KIND


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])


class SAMStaticPlugin(SAMPluginCommon):
    """Smarter API Manifest - Plugin"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    spec: SAMPluginStaticSpec = Field(
        ...,
        description=f"{class_identifier}.{SAMKeys.SPEC.value}[obj]: Required, the {MANIFEST_KIND} specification.",
    )
