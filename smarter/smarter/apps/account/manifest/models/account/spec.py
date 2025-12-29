"""Smarter API Manifest - Plugin.spec"""

import os
import re
import zoneinfo
from typing import ClassVar, Optional

import pycountry
from pydantic import Field, field_validator

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.common.exceptions import SmarterValueError
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
        "US",
        description=(f"{class_identifier}.country[str]. The country for the {MANIFEST_KIND}. Default: USA."),
    )
    language: str = Field(
        "en-US",
        description=(
            f"{class_identifier}.language[str]. The primary language for the {MANIFEST_KIND}. Default: en-US."
        ),
    )
    timezone: str = Field(
        "America/New_York",
        description=(
            f"{class_identifier}.timezone[str]. The primary timezone for the {MANIFEST_KIND}. Default: America/New_York."
        ),
    )
    currency: str = Field(
        "USD",
        description=(f"{class_identifier}.currency[str]. The primary currency for the {MANIFEST_KIND}. Default: USD."),
    )

    @field_validator("currency")
    def validate_currency(cls, v):
        if not pycountry.currencies.get(alpha_3=v):
            raise SmarterValueError("Invalid currency code")
        return v

    @field_validator("country")
    def validate_country(cls, v):
        if not pycountry.countries.get(alpha_2=v) and not pycountry.countries.get(alpha_3=v):
            raise SmarterValueError("Invalid country code")
        return v

    @field_validator("language")
    def validate_language(cls, v):
        # Accept BCP 47 like 'en' or 'en-US', validate language and region (country) if present
        parts = v.split("-")
        lang_code = parts[0]
        lang = pycountry.languages.get(alpha_2=lang_code) or pycountry.languages.get(alpha_3=lang_code)
        if not lang:
            raise SmarterValueError("Invalid language code")
        if len(parts) > 1:
            region_code = parts[1]
            if not pycountry.countries.get(alpha_2=region_code):
                raise SmarterValueError("Invalid region code in language tag")
        return v

    @field_validator("timezone")
    def validate_timezone(cls, v):
        try:
            zoneinfo.ZoneInfo(v)
        except Exception as e:
            raise SmarterValueError("Invalid timezone") from e
        return v


class SAMAccountSpec(AbstractSAMSpecBase):
    """Smarter API Account Manifest Account.spec"""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMAccountSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."),
    )
