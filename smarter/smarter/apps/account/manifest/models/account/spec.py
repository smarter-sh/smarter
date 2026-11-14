"""Smarter API Manifest - Plugin.spec."""

import os
import zoneinfo
from typing import ClassVar, Optional

import pycountry
from pydantic import Field, field_validator

from smarter.apps.account.manifest.models.account.const import MANIFEST_KIND
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMAccountSpecConfig(AbstractSAMSpecBase):
    """Smarter API Account Manifest Account.spec.config."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".configuration"

    companyName: str = Field(
        ...,
        description=(
            f"{class_identifier}.companyName[str]. The legal entity of your Smarter {MANIFEST_KIND} for invoicing and legal correspondence."
        ),
    )
    phoneNumber: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.phoneNumber[str]. The primary phone number for the {MANIFEST_KIND}."),
    )
    address1: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.address1[str]. The primary address for the {MANIFEST_KIND}."),
    )
    address2: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.address2[str]. Optional. The secondary address for the {MANIFEST_KIND}."),
    )
    city: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.city[str]. The city for the {MANIFEST_KIND}."),
    )
    state: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.state[str]. The state for the {MANIFEST_KIND}."),
    )
    postalCode: Optional[str] = Field(
        None,
        description=(f"{class_identifier}.postalCode[str]. The postal code for the {MANIFEST_KIND}."),
    )
    country: str = Field(
        "US",
        description=(
            f"{class_identifier}.country[str]. The ISO 3166 country code for the {MANIFEST_KIND}. Default: USA."
        ),
    )
    language: str = Field(
        "en-US",
        description=(
            f"{class_identifier}.language[str]. The primary BCP 47 language tag for the {MANIFEST_KIND}. Default: en-US."
        ),
    )
    timezone: str = Field(
        "America/New_York",
        description=(
            f"{class_identifier}.timezone[str]. The primary IANA timezone for the {MANIFEST_KIND}. Default: America/New_York."
        ),
    )
    currency: str = Field(
        "USD",
        description=(
            f"{class_identifier}.currency[str]. The primary ISO 4217 currency for the {MANIFEST_KIND}. Default: USD."
        ),
    )

    @field_validator("currency")
    def validate_currency(cls, v):
        """
        Check that the currency is an ISO 4217 code, e.g. ``USD``.

        :param v: The currency code.
        :returns: The currency code.
        :raises SmarterValueError: when it is not an ISO 4217 code.
        """
        if not pycountry.currencies.get(alpha_3=v):
            raise SmarterValueError("Invalid ISO 4217 currency code. Use 3-letter code. Example: 'USD'")
        return v

    @field_validator("country")
    def validate_country(cls, v):
        """
        Check that the country is an ISO 3166 two- or three-letter code, e.g. ``US`` or ``USA``.

        :param v: The country code.
        :returns: The country code.
        :raises SmarterValueError: when it is not an ISO 3166 code.
        """
        if not pycountry.countries.get(alpha_2=v) and not pycountry.countries.get(alpha_3=v):
            raise SmarterValueError(
                "Invalid ISO 3166 country code. Use 2-letter or 3-letter code. Example: 'US' or 'USA'"
            )
        return v

    @field_validator("language")
    def validate_language(cls, v):
        """
        Check that the language is a BCP 47 tag, e.g. ``en`` or ``en-US``.

        The language must be an ISO 639 code, and the region, if any, an ISO 3166 two-letter code.

        :param v: The language tag.
        :returns: The language tag.
        :raises SmarterValueError: when the language or the region is not valid.
        """
        # Accept BCP 47 like 'en' or 'en-US', validate language and region (country) if present
        parts = v.split("-")
        lang_code = parts[0]
        lang = pycountry.languages.get(alpha_2=lang_code) or pycountry.languages.get(alpha_3=lang_code)
        if not lang:
            raise SmarterValueError("Invalid language code")
        if len(parts) > 1:
            region_code = parts[1]
            if not pycountry.countries.get(alpha_2=region_code):
                raise SmarterValueError("Invalid BCP 47 language tag. Example: 'en' or 'en-US'")
        return v

    @field_validator("timezone")
    def validate_timezone(cls, v):
        """
        Check that the timezone is an IANA timezone, e.g. ``America/New_York``.

        :param v: The timezone.
        :returns: The timezone.
        :raises SmarterValueError: when :class:`zoneinfo.ZoneInfo` does not know it.
        """
        try:
            zoneinfo.ZoneInfo(v)
        except Exception as e:
            raise SmarterValueError("Invalid IANA timezone. Example: 'America/New_York'") from e
        return v

    parent: Optional[str] = Field(
        None,
        description=(
            f"{class_identifier}.parent[str]. Optional. The account number of the {MANIFEST_KIND} above this one in "
            "its organization, e.g. a department's company. Omitted means directly under the Smarter account, the "
            "root of the account tree."
        ),
    )
    shareScope: Optional[str] = Field(
        None,
        description=(
            f"{class_identifier}.shareScope[str]. Optional. The account number of this {MANIFEST_KIND} or one of "
            "its ancestors, whose whole subtree may read this account's resources, e.g. an IT department that "
            "shares its Secrets and Connections with its company. Omitted means that the account shares nothing."
        ),
    )

    @field_validator("parent", "shareScope")
    def validate_account_reference(cls, v):
        """
        Check that ``parent`` and ``shareScope`` are account numbers, e.g. ``1234-5678-9012``.

        :param v: The account number, or None.
        :returns: The account number, or None.
        :raises SmarterValueError: when it is not an account number.
        """
        if v is None:
            return v
        if not SmarterValidator.is_valid_account_number(v):
            raise SmarterValueError("Invalid account number. Example: '1234-5678-9012'")
        return v


class SAMAccountSpec(AbstractSAMSpecBase):
    """Smarter API Account Manifest Account.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMAccountSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."),
    )
