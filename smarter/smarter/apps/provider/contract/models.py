"""
Pydantic models of the Providers' REST api responses (``/api/v1/providers/``).

The REST api's views build their responses from these models, and the Smarter api's OpenAPI
document (:mod:`smarter.apps.api.v1.contract.openapi`) publishes their JSON Schemas.

:class:`ProviderApiProvider` and :class:`ProviderApiModel` are the rows, as
:mod:`smarter.apps.provider.serializers` returned them before the api was modeled, which clients
already read: a Provider's api key is its Secret's name and status, never the key.

The models forbid extra fields: the api returns exactly what they declare.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional

from pydantic import Field

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUser,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete
from smarter.apps.secret.contract.models import SecretApiSecretRef

if TYPE_CHECKING:
    from smarter.apps.provider.models import Provider, ProviderModel


ProviderApiStatus = Literal["unverified", "verifying", "failed", "verified", "suspended", "deprecated"]
"""The choices of ``Provider.status``.

A test fails if the two differ.
"""


class ProviderApiProvider(AccountApiModel):
    """An LLM provider: a :class:`smarter.apps.provider.models.Provider`."""

    id: int = Field(..., description="The row's primary key.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="The Provider's name, e.g. openai.")
    user_profile: AccountApiUserProfile = Field(..., description="The Provider's owner.")
    status: ProviderApiStatus = Field(..., description="The Provider's verification status.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    manifest_url: Optional[str] = Field(None, description="The url of the Provider's manifest in the web console.")
    ready: bool = Field(..., description="Whether the Provider can be used.")
    is_default: bool
    is_active: bool
    is_verified: bool
    is_featured: bool
    is_deprecated: bool
    is_flagged: bool
    is_suspended: bool
    base_url: Optional[str] = Field(None, description="The base url of the provider's api.")
    api_key: Optional[SecretApiSecretRef] = Field(None, description="The Secret of its api key, never the key.")
    default_model: Optional[str] = Field(None, description="The model that LLMClients use by default.")
    connectivity_test_path: Optional[str] = Field(None, description="The path that tests the provider's api.")
    logo: Optional[str] = Field(None, description="The url of the provider's logo.")
    website_url: Optional[str] = None
    ownership_requested: Optional[str] = Field(None, description="The email of a pending ownership request.")
    contact_email: Optional[str] = None
    contact_email_verified: Optional[datetime] = None
    support_email: Optional[str] = None
    support_email_verified: Optional[datetime] = None
    docs_url: Optional[str] = None
    terms_of_service_url: Optional[str] = None
    privacy_policy_url: Optional[str] = None
    is_official_provider: bool = Field(..., description="Whether the platform's owner publishes the Provider.")
    tos_accepted: bool = Field(..., description="Whether the provider's terms of service were accepted.")
    tos_accepted_at: Optional[datetime] = None
    tos_accepted_by: Optional[AccountApiUser] = Field(None, description="Who accepted the terms of service.")
    rfc1034_compliant_name: Optional[str] = Field(None, description="The name, as a DNS label.")
    can_delete: bool = Field(..., description="Whether the requesting user may delete the Provider now.")

    @classmethod
    def from_model(cls, provider: "Provider", user: object = None) -> "ProviderApiProvider":
        """
        The contract's model of a Provider.

        :param provider: The row, whose ``user_profile``, ``api_key`` and ``tos_accepted_by`` should be fetched with it.
        :type provider: smarter.apps.provider.models.Provider
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: ProviderApiProvider
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.provider.manifest.models.provider.const import (
            MANIFEST_KIND as PROVIDER_KIND,
        )

        return cls(
            id=provider.pk,
            created_at=provider.created_at,
            updated_at=provider.updated_at,
            name=provider.name,
            user_profile=AccountApiUserProfile.from_model(provider.user_profile),
            status=provider.status,  # type: ignore[arg-type]
            description=provider.description,
            version=provider.version,
            annotations=provider.annotations,
            tags=[tag.name for tag in provider.tags.all()],
            manifest_url=provider.manifest_url,
            ready=provider.ready,
            is_default=provider.is_default,
            is_active=provider.is_active,
            is_verified=provider.is_verified,
            is_featured=provider.is_featured,
            is_deprecated=provider.is_deprecated,
            is_flagged=provider.is_flagged,
            is_suspended=provider.is_suspended,
            base_url=provider.base_url,
            api_key=SecretApiSecretRef.from_model(provider.api_key, user) if provider.api_key else None,
            default_model=provider.default_model,
            connectivity_test_path=provider.connectivity_test_path,
            logo=provider.logo.url if provider.logo else None,
            website_url=provider.website_url,
            ownership_requested=provider.ownership_requested,
            contact_email=provider.contact_email,
            contact_email_verified=provider.contact_email_verified,
            support_email=provider.support_email,
            support_email_verified=provider.support_email_verified,
            docs_url=provider.docs_url,
            terms_of_service_url=provider.terms_of_service_url,
            privacy_policy_url=provider.privacy_policy_url,
            is_official_provider=provider.is_official_provider,
            tos_accepted=provider.tos_accepted,
            tos_accepted_at=provider.tos_accepted_at,
            tos_accepted_by=AccountApiUser.from_model(provider.tos_accepted_by) if provider.tos_accepted_by else None,
            rfc1034_compliant_name=provider.rfc1034_compliant_name,
            can_delete=user_can_delete(provider, PROVIDER_KIND, user),
        )


class ProviderApiModel(AccountApiModel):
    """A model of an LLM provider: a :class:`smarter.apps.provider.models.ProviderModel`, with its provider."""

    id: int = Field(..., description="The row's primary key.")
    provider: ProviderApiProvider
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")
    name: str = Field(..., description="The model's name, e.g. gpt-4o.")
    description: Optional[str] = None
    is_default: bool
    is_active: bool
    is_deprecated: bool
    is_flagged: bool
    is_suspended: bool
    max_completion_tokens: int = Field(..., ge=0)
    temperature: float
    top_p: float
    supports_text_input: bool
    supports_text_generation: bool
    supports_translation: bool
    supports_summarization: bool
    supports_streaming: bool
    supports_tools: bool
    supports_image_input: bool
    supports_audio_input: bool
    supports_embedding: bool
    supports_fine_tuning: bool
    supports_search: bool
    supports_code_interpreter: bool
    supports_image_generation: bool
    supports_audio_generation: bool

    @classmethod
    def from_model(cls, provider_model: "ProviderModel", user: object = None) -> "ProviderApiModel":
        """
        The contract's model of a provider's model.

        :param provider_model: The row, whose ``provider`` should be fetched with it.
        :type provider_model: smarter.apps.provider.models.ProviderModel
        :param user: The requesting user, for the provider's ``can_delete``.
        :type user: object
        :returns: The model.
        :rtype: ProviderApiModel
        """
        fields = {
            name: getattr(provider_model, name)
            for name in cls.model_fields
            if name not in ("id", "provider", "created_at", "updated_at")
        }
        return cls(
            id=provider_model.pk,
            provider=ProviderApiProvider.from_model(provider_model.provider, user),
            created_at=provider_model.created_at,
            updated_at=provider_model.updated_at,
            **fields,
        )


PROVIDER_API_MODELS = (ProviderApiProvider, ProviderApiModel)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""

__all__ = ["PROVIDER_API_MODELS", "ProviderApiModel", "ProviderApiProvider", "ProviderApiStatus"]
