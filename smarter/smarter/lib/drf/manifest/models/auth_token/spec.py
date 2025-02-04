"""Smarter API SmarterAuthToken - SmarterAuthToken.spec"""

import os
from typing import ClassVar

from pydantic import Field

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMSmarterAuthTokenSpecConfig(AbstractSAMSpecBase):
    """Smarter API SmarterAuthToken Manifest SmarterAuthToken.spec.config"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    isActive: bool = Field(
        default=False,
        description=f"{class_identifier}.isActive[bool]. Required. Whether the {MANIFEST_KIND} is activated.",
    )
    username: str = Field(
        ...,
        description=f"{class_identifier}.username[str]. The Smarter username to which this {MANIFEST_KIND} is attached.",
    )


class SAMSmarterAuthTokenSpec(AbstractSAMSpecBase):
    """Smarter API SmarterAuthToken Manifest SmarterAuthToken.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMSmarterAuthTokenSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."),
    )
