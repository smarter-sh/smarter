"""Smarter API Manifest - Plugin.spec"""

import os
from typing import ClassVar, Optional

from pydantic import Field

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.lib.manifest.models import AbstractSAMSpecBase


filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMAccountSpecConfig(AbstractSAMSpecBase):
    """Smarter API Account Manifest Account.spec.config"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    companyName: str = Field(
        ...,
        description=(
            f"{class_identifier}.companyName[str]. The legal entity of your Smarter {MANIFEST_KIND} for invoicing and legal correspondence."
        ),
    )
    phoneNumber: str = Field(
        ...,
        description=(f"{class_identifier}.phoneNumber[str]. The primary phone number for the {MANIFEST_KIND}."),
    )
    address1: str = Field(
        ...,
        description=(f"{class_identifier}.address1[str]. The primary address for the {MANIFEST_KIND}."),
    )
    address2: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.address2[str]. Optional. The secondary address for the {MANIFEST_KIND}."),
    )
    city: str = Field(
        ...,
        description=(f"{class_identifier}.city[str]. The city for the {MANIFEST_KIND}."),
    )
    state: str = Field(
        ...,
        description=(f"{class_identifier}.state[str]. The state for the {MANIFEST_KIND}."),
    )
    postalCode: str = Field(
        ...,
        description=(f"{class_identifier}.postalCode[str]. The postal code for the {MANIFEST_KIND}."),
    )
    country: str = Field(
        ...,
        description=(f"{class_identifier}.country[str]. The country for the {MANIFEST_KIND}."),
    )
    language: str = Field(
        ...,
        description=(f"{class_identifier}.language[str]. The primary language for the {MANIFEST_KIND}."),
    )
    timezone: str = Field(
        ...,
        description=(f"{class_identifier}.timezone[str]. The primary timezone for the {MANIFEST_KIND}."),
    )
    currency: str = Field(
        ...,
        description=(f"{class_identifier}.currency[str]. The primary currency for the {MANIFEST_KIND}."),
    )


class SAMAccountSpec(AbstractSAMSpecBase):
    """Smarter API Account Manifest Account.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMAccountSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."),
    )
