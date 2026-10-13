"""
Pydantic models of the Secrets' REST api responses (``/api/v1/secrets/``).

A Secret's response is its metadata. Its value is never returned.

:class:`SecretApiSecret` is a Secret, as :class:`smarter.apps.secret.serializers.SecretSerializer`
returned it before the api was modeled, which clients already read. One value changed: its
``canDelete`` is computed for the requesting user. The serializer was called without a request, so
it was always false.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import Field

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete

if TYPE_CHECKING:
    from smarter.apps.secret.models import Secret


class SecretApiSecret(AccountApiModel):
    """A Secret's metadata: a :class:`smarter.apps.secret.models.Secret`, without its value."""

    id: int = Field(..., description="The row's primary key.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case, e.g. openai_api_key.")
    user_profile: AccountApiUserProfile = Field(..., description="The Secret's owner.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    manifest_url: Optional[str] = Field(None, description="The url of the Secret's manifest in the web console.")
    ready: bool = Field(..., description="Whether the Secret has a value that can be decrypted.")
    expires_at: Optional[datetime] = Field(None, description="When the Secret expires, if it does.")
    last_accessed: Optional[datetime] = Field(None, description="When the platform last read its value.")
    can_delete: bool = Field(
        ..., description="Whether the requesting user may delete the Secret now: they own it, and nothing uses it."
    )

    @classmethod
    def from_model(cls, secret: "Secret", user: object = None) -> "SecretApiSecret":
        """
        The contract's model of a Secret.

        :param secret: The row, whose ``user_profile`` should be fetched with it.
        :type secret: smarter.apps.secret.models.Secret
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: SecretApiSecret
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.secret.manifest.models.secret.const import (
            MANIFEST_KIND as SECRET_KIND,
        )

        return cls(
            id=secret.pk,
            created_at=secret.created_at,
            updated_at=secret.updated_at,
            name=secret.name,
            user_profile=AccountApiUserProfile.from_model(secret.user_profile),
            description=secret.description,
            version=secret.version,
            annotations=secret.annotations,
            tags=[tag.name for tag in secret.tags.all()],
            manifest_url=secret.manifest_url,
            ready=secret.ready,
            expires_at=secret.expires_at,
            last_accessed=secret.last_accessed,
            can_delete=user_can_delete(secret, SECRET_KIND, user),
        )


class SecretApiSecretRef(AccountApiModel):
    """A Secret, as another resource refers to it, e.g. a Provider's api key: its name, never its value."""

    id: int = Field(..., description="The Secret's primary key.")
    name: str = Field(..., description="The Secret's name.")
    manifest_url: Optional[str] = Field(None, description="The url of the Secret's manifest in the web console.")
    ready: bool = Field(..., description="Whether the Secret has a value that can be decrypted.")
    can_delete: bool = Field(..., description="Whether the requesting user may delete the Secret now.")

    @classmethod
    def from_model(cls, secret: "Secret", user: object = None) -> "SecretApiSecretRef":
        """
        The contract's reference to a Secret.

        :param secret: The row.
        :type secret: smarter.apps.secret.models.Secret
        :param user: The requesting user, for ``can_delete``.
        :type user: object
        :returns: The model.
        :rtype: SecretApiSecretRef
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.secret.manifest.models.secret.const import (
            MANIFEST_KIND as SECRET_KIND,
        )

        return cls(
            id=secret.pk,
            name=secret.name,
            manifest_url=secret.manifest_url,
            ready=secret.ready,
            can_delete=user_can_delete(secret, SECRET_KIND, user),
        )


SECRET_API_MODELS = (SecretApiSecret,)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""

__all__ = ["SECRET_API_MODELS", "SecretApiSecret", "SecretApiSecretRef"]
