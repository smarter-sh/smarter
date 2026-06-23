"""Smarter API Proxy Manifest - Proxy.spec."""

import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.apps.plugin.manifest.models.static_plugin.const import MANIFEST_KIND
from smarter.lib.manifest.models import SmarterBasePydanticModel

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMProxySpec(SAMPluginCommonSpec):
    """Smarter API Proxy Manifest Proxy.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER
