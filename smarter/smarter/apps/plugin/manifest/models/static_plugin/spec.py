"""Smarter API Manifest - Plugin.spec"""

import os
from typing import ClassVar, Optional

from pydantic import BaseModel, Field

from smarter.apps.plugin.manifest.enum import (
    SAMPluginCommonMetadataClassValues,
    SAMPluginSpecKeys,
)
from smarter.apps.plugin.manifest.models.common.plugin.spec import SAMPluginCommonSpec
from smarter.apps.plugin.manifest.models.static_plugin.const import MANIFEST_KIND


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 8192  # this is actually the overall max token count for OpenAI chatGPT-4


class SAMPluginStaticSpecData(BaseModel):
    """Smarter API Plugin Manifest Plugin.spec.data"""

    class_identifier: ClassVar[str] = f"{MODULE_IDENTIFIER}.{SAMPluginSpecKeys.DATA.value}"

    description: str = Field(
        ...,
        description=(
            f"{class_identifier}.description[str]: A narrative description of the {MANIFEST_KIND} features "
            "that is provided to the LLM as part of a tool_chain dict"
        ),
    )
    staticData: Optional[dict] = Field(
        None,
        description=(
            f"{class_identifier}.staticData[obj]: The static data returned by the {MANIFEST_KIND} when the "
            f"class is '{SAMPluginCommonMetadataClassValues.STATIC.value}'. LLM's are adept at understanding the context of "
            "json data structures. Try to provide granular and specific data elements."
        ),
    )


class SAMPluginStaticSpec(SAMPluginCommonSpec):
    """Smarter API Plugin Manifest Plugin.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    data: SAMPluginStaticSpecData = Field(
        ...,
        description=(
            f"{class_identifier}.data[obj]: the json data returned by the {MANIFEST_KIND}. "
            f"This should be one of the following kinds: {SAMPluginCommonMetadataClassValues.all_values()}"
        ),
    )
