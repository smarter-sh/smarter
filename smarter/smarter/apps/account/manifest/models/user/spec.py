"""Smarter API Manifest - User.spec."""

import os
from typing import ClassVar, Optional

from pydantic import Field, field_validator

from smarter.apps.account.manifest.models.user.const import MANIFEST_KIND
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.validators import SmarterValidator
from smarter.lib.manifest.models import AbstractSAMSpecBase

filename = os.path.splitext(os.path.basename(__file__))[0]
MODULE_IDENTIFIER = f"{MANIFEST_KIND}.{filename}"


class SAMUserSpecConfig(AbstractSAMSpecBase):
    """Smarter API User Manifest User.spec.config."""

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


class SAMUserAccountMembership(AbstractSAMSpecBase):
    """Smarter API User Manifest User.spec.accounts[]: the user's membership of one account."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER + ".accounts"

    accountNumber: str = Field(
        ...,
        description=(
            f"{class_identifier}.accountNumber[str]. The number of an account that the {MANIFEST_KIND} belongs to."
        ),
    )
    isAccountAdmin: bool = Field(
        False,
        description=(
            f"{class_identifier}.isAccountAdmin[bool]. Optional. Whether the {MANIFEST_KIND} administers this account, "
            "and only this one: manages every resource in it. Default: false."
        ),
    )

    @field_validator("accountNumber")
    def validate_account_number(cls, v):
        """
        Check that the account number has the form 1234-5678-9012.

        :param v: The account number.
        :returns: The account number.
        :raises SmarterValueError: when it is not an account number.
        """
        if not SmarterValidator.is_valid_account_number(v):
            raise SmarterValueError("Invalid account number. Example: '1234-5678-9012'")
        return v


class SAMUserSpec(AbstractSAMSpecBase):
    """Smarter API User Manifest User.spec."""

    class_identifier: ClassVar[str] = MODULE_IDENTIFIER

    config: SAMUserSpecConfig = Field(
        ...,
        description=(f"{class_identifier}.config[object]. The configuration for the {MANIFEST_KIND}."),
    )
    accounts: Optional[list[SAMUserAccountMembership]] = Field(
        None,
        description=(
            f"{class_identifier}.accounts[list]. Optional. The accounts that the {MANIFEST_KIND} belongs to, e.g. the "
            "departments of an organization, each with whether the user administers it. Omitted, the user belongs to "
            "the account of whoever applies the manifest. Apply adds each membership that is missing and updates the "
            "others, but never removes one, which would delete every resource that the user owns in that account. "
            "A superuser may list any account; anyone else only accounts that they administer."
        ),
    )

    @field_validator("accounts")
    def validate_accounts(cls, v):
        """
        Check that no account is listed twice.

        :param v: The memberships, or None.
        :returns: The memberships, or None.
        :raises SmarterValueError: when an account is listed more than once.
        """
        if v is None:
            return v
        account_numbers = [membership.accountNumber for membership in v]
        if len(account_numbers) != len(set(account_numbers)):
            raise SmarterValueError("Each account may be listed only once in accounts.")
        return v
