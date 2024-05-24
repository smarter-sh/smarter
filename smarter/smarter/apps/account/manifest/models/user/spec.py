"""Smarter API Manifest - User.spec"""

import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"
SMARTER_PLUGIN_MAX_SYSTEM_ROLE_LENGTH = 2048


class SAMUserSpecConfig(AbstractSAMSpecBase):
    """Smarter API User Manifest User.spec.config"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    firstName: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.firstName[str]. Optional. The first name of the {MANIFEST_KIND}."),
    )
    lastName: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.lastName[str]. Optional. The last name of the {MANIFEST_KIND}."),
    )
    email: str = Field(
        ...,
        description=(f"{class_identifier}.email[str]. The email address of the {MANIFEST_KIND}."),
    )
    isStaff: Optional[bool] = Field(
        False,
        description=(
            f"{class_identifier}.isStaff[bool]. Optional. Designates whether the {MANIFEST_KIND} has admin permissions."
        ),
    )
    isActive: bool = Field(
        ...,
        description=(
            f"{class_identifier}.isActive[bool]. Designates whether this {MANIFEST_KIND} should be treated as active."
        ),
    )


class SAMUserSpec(AbstractSAMSpecBase):
    """Smarter API User Manifest User.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMUserSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."),
    )
