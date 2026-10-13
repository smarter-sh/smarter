"""
Pydantic models of the account data that the REST api's responses include.

A resource that a user owns, e.g. an LLMClient or a plugin, is returned with its owner, as
:class:`AccountApiUserProfile`: the owner's username and email, and their account's number. It is
the output of :class:`smarter.apps.account.serializers.UserProfileSerializer`, which the REST api
returned before it was modeled, and which clients already read.

The accounts' REST api (``/api/v1/accounts/``), which only superusers may call, returns accounts
(:class:`AccountApiAccountDetail`), users (:class:`AccountApiUserDetail`), user profiles
(:class:`AccountApiProfile`) and account contacts (:class:`AccountApiContact`): the outputs of
:class:`smarter.apps.account.serializers.AccountSerializer`, ``UserSerializer`` and
``AccountContactSerializer``, which clients already read.

The models forbid extra fields: the api returns exactly what they declare.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from smarter.apps.account.models import Account, AccountContact
    from smarter.apps.account.models import User as UserModel
    from smarter.apps.account.models import UserProfile


MetaDataApiAnnotations = Optional[Union[list[dict[str, JsonValue]], dict[str, JsonValue]]]
"""
``MetaDataModel.annotations``: a list of key-value pairs, e.g. ``[{"smarter.sh/purpose": "example"}]``, or,.

in legacy rows, an object.
"""


class AccountApiModel(BaseModel):
    """
    Base class of the account contract's models.

    The api's JSON is camelCase, e.g. ``accountNumber``. The models' fields are snake_case, and
    their camelCase aliases are what they validate and dump.
    """

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
    )


class AccountApiUser(AccountApiModel):
    """A user, as the owner of a resource: a :class:`django.contrib.auth.models.User`'s username and email."""

    username: str = Field(..., description="User.username.")
    email: Optional[str] = Field(None, description="User.email.")

    @classmethod
    def from_model(cls, user: "UserModel") -> "AccountApiUser":
        """
        The contract's model of a user.

        :param user: The row.
        :type user: django.contrib.auth.models.User
        :returns: The model.
        :rtype: AccountApiUser
        """
        return cls(username=user.username, email=user.email)


class AccountApiAccount(AccountApiModel):
    """An account, as the owner of a resource: a :class:`smarter.apps.account.models.Account`'s number."""

    account_number: str = Field(..., description="Account.account_number, e.g. 1234-5678-9012.")

    @classmethod
    def from_model(cls, account: "Account") -> "AccountApiAccount":
        """
        The contract's model of an account.

        :param account: The row.
        :type account: smarter.apps.account.models.Account
        :returns: The model.
        :rtype: AccountApiAccount
        """
        return cls(account_number=account.account_number)


class AccountApiUserProfile(AccountApiModel):
    """The owner of a resource: a :class:`smarter.apps.account.models.UserProfile`'s user and account."""

    user: AccountApiUser
    account: AccountApiAccount

    @classmethod
    def from_model(cls, user_profile: "UserProfile") -> "AccountApiUserProfile":
        """
        The contract's model of a resource's owner.

        :param user_profile: The row, whose ``user`` and ``account`` should be fetched with it.
        :type user_profile: smarter.apps.account.models.UserProfile
        :returns: The model.
        :rtype: AccountApiUserProfile
        """
        return cls(
            user=AccountApiUser.from_model(user_profile.user),
            account=AccountApiAccount.from_model(user_profile.account),
        )


class AccountApiAccountDetail(AccountApiModel):
    """An account: a :class:`smarter.apps.account.models.Account`."""

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The account's hashed id, e.g. rMTAwMDAwMQx.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    account_number: Optional[str] = Field(None, description="Account.account_number, e.g. 1234-5678-9012.")
    is_default_account: bool = Field(..., description="Account.is_default_account.")
    company_name: str = Field(..., description="Account.company_name.")
    phone_number: Optional[str] = Field(None, description="Account.phone_number.")
    address1: Optional[str] = Field(None, description="Account.address1.")
    address2: Optional[str] = Field(None, description="Account.address2.")
    city: Optional[str] = Field(None, description="Account.city.")
    state: Optional[str] = Field(None, description="Account.state.")
    postal_code: Optional[str] = Field(None, description="Account.postal_code.")
    country: Optional[str] = Field(None, description="Account.country.")
    language: Optional[str] = Field(None, description="Account.language, e.g. EN.")
    timezone: Optional[str] = Field(None, description="Account.timezone, e.g. America/Denver.")
    currency: Optional[str] = Field(None, description="Account.currency, e.g. USD.")
    is_active: bool = Field(..., description="Account.is_active.")

    @classmethod
    def from_model(cls, account: "Account") -> "AccountApiAccountDetail":
        """
        The contract's model of an account.

        :param account: The row.
        :type account: smarter.apps.account.models.Account
        :returns: The model.
        :rtype: AccountApiAccountDetail
        """
        return cls(
            id=account.pk,
            hashed_id=account.hashed_id,
            created_at=account.created_at,
            updated_at=account.updated_at,
            name=account.name,
            description=account.description,
            version=account.version,
            tags=[tag.name for tag in account.tags.all()],
            annotations=account.annotations,
            account_number=account.account_number,
            is_default_account=account.is_default_account,
            company_name=account.company_name,
            phone_number=account.phone_number,
            address1=account.address1,
            address2=account.address2,
            city=account.city,
            state=account.state,
            postal_code=account.postal_code,
            country=account.country,
            language=account.language,
            timezone=account.timezone,
            currency=account.currency,
            is_active=account.is_active,
        )


class AccountApiUserDetail(AccountApiModel):
    """A user: a :class:`django.contrib.auth.models.User`, without its password and permissions."""

    id: int = Field(..., description="The row's primary key.")
    username: str = Field(..., description="User.username.")
    first_name: str = Field("", description="User.first_name.")
    last_name: str = Field("", description="User.last_name.")
    email: str = Field("", description="User.email.")
    is_staff: bool = Field(..., description="User.is_staff: whether the user administers their account.")
    is_superuser: bool = Field(..., description="User.is_superuser: whether the user administers the platform.")

    @classmethod
    def from_model(cls, user: "UserModel") -> "AccountApiUserDetail":
        """
        The contract's model of a user.

        :param user: The row.
        :type user: django.contrib.auth.models.User
        :returns: The model.
        :rtype: AccountApiUserDetail
        """
        return cls(
            id=user.pk,
            username=user.username,
            first_name=user.first_name,
            last_name=user.last_name,
            email=user.email,
            is_staff=user.is_staff,
            is_superuser=user.is_superuser,
        )


class AccountApiProfile(AccountApiModel):
    """A user's membership of an account: a :class:`smarter.apps.account.models.UserProfile`."""

    id: int = Field(..., description="The row's primary key.")
    hashed_id: str = Field(..., description="The user profile's hashed id.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user: AccountApiUserDetail = Field(..., description="UserProfile.user.")
    account: AccountApiAccount = Field(..., description="UserProfile.account.")
    profile_image_url: Optional[str] = Field(None, description="UserProfile.profile_image_url.")
    is_test: bool = Field(..., description="UserProfile.is_test: whether a test created it.")

    @classmethod
    def from_model(cls, user_profile: "UserProfile") -> "AccountApiProfile":
        """
        The contract's model of a user profile.

        :param user_profile: The row, whose ``user`` and ``account`` should be fetched with it.
        :type user_profile: smarter.apps.account.models.UserProfile
        :returns: The model.
        :rtype: AccountApiProfile
        """
        return cls(
            id=user_profile.pk,
            hashed_id=user_profile.hashed_id,
            created_at=user_profile.created_at,
            updated_at=user_profile.updated_at,
            name=user_profile.name,
            description=user_profile.description,
            version=user_profile.version,
            tags=[tag.name for tag in user_profile.tags.all()],
            annotations=user_profile.annotations,
            user=AccountApiUserDetail.from_model(user_profile.user),
            account=AccountApiAccount.from_model(user_profile.account),
            profile_image_url=user_profile.profile_image_url,
            is_test=user_profile.is_test,
        )


class AccountApiContact(AccountApiModel):
    """A contact of an account, who receives its notices: a :class:`smarter.apps.account.models.AccountContact`."""

    id: int = Field(..., description="The row's primary key.")
    account: AccountApiAccount = Field(..., description="AccountContact.account.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    first_name: str = Field(..., description="AccountContact.first_name.")
    last_name: str = Field(..., description="AccountContact.last_name.")
    email: str = Field(..., description="AccountContact.email.")
    phone: Optional[str] = Field(None, description="AccountContact.phone.")
    is_primary: bool = Field(..., description="AccountContact.is_primary: whether it is the account's main contact.")
    is_test: bool = Field(..., description="AccountContact.is_test: whether a test created it.")
    welcomed: bool = Field(..., description="AccountContact.welcomed: whether it was sent the welcome email.")

    @classmethod
    def from_model(cls, contact: "AccountContact") -> "AccountApiContact":
        """
        The contract's model of an account contact.

        :param contact: The row, whose ``account`` should be fetched with it.
        :type contact: smarter.apps.account.models.AccountContact
        :returns: The model.
        :rtype: AccountApiContact
        """
        return cls(
            id=contact.pk,
            account=AccountApiAccount.from_model(contact.account),
            created_at=contact.created_at,
            updated_at=contact.updated_at,
            first_name=contact.first_name,
            last_name=contact.last_name,
            email=contact.email,
            phone=contact.phone,
            is_primary=contact.is_primary,
            is_test=contact.is_test,
            welcomed=contact.welcomed,
        )


ACCOUNT_API_MODELS = (AccountApiAccountDetail, AccountApiUserDetail, AccountApiProfile, AccountApiContact)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""


__all__ = [
    "ACCOUNT_API_MODELS",
    "AccountApiAccount",
    "AccountApiAccountDetail",
    "AccountApiContact",
    "AccountApiModel",
    "AccountApiProfile",
    "AccountApiUser",
    "AccountApiUserDetail",
    "AccountApiUserProfile",
    "MetaDataApiAnnotations",
]
