"""
Pydantic models of the account data that the REST api's responses include.

A resource that a user owns, e.g. an LLMClient or a plugin, is returned with its owner, as
:class:`AccountApiUserProfile`: the owner's username and email, and their account's number. It is
the output of :class:`smarter.apps.account.serializers.UserProfileSerializer`, which the REST api
returned before it was modeled, and which clients already read.

The models forbid extra fields: the api returns exactly what they declare.
"""

from typing import TYPE_CHECKING, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic.alias_generators import to_camel

if TYPE_CHECKING:
    from smarter.apps.account.models import Account
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


__all__ = ["AccountApiAccount", "AccountApiModel", "AccountApiUser", "AccountApiUserProfile", "MetaDataApiAnnotations"]
