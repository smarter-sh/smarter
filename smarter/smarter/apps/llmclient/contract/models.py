"""
Pydantic models of the LLMClients' REST api responses (``/api/v1/llm-clients/``).

The REST api's views build their responses from these models, and the Smarter api's OpenAPI
document (:mod:`smarter.apps.api.v1.contract.openapi`) publishes their JSON Schemas. Each model
is built from its row by ``from_model()``.

They describe the JSON that :mod:`smarter.apps.llmclient.serializers` produced before the api
was modeled, which clients already read: camelCase keys, an LLMClient's owner nested rather than
its id, and an LLMClient's related rows inline. Two values changed: ``canDelete`` is computed for
the requesting user, where the serializers, called without a request, always said false, and an api
key's ``apiKey`` is its token's public ``key_id``, where it was the token's digest.

The models forbid extra fields: the api returns exactly what they declare. Adding a field is
backward compatible. Removing or renaming one is not.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Literal, Optional
from uuid import UUID

from pydantic import Field, JsonValue

from smarter.apps.account.contract.models import (
    AccountApiModel,
    AccountApiUserProfile,
    MetaDataApiAnnotations,
)
from smarter.apps.account.serializers import user_can_delete
from smarter.apps.llmtool.contract.models import PluginApiPluginMeta

if TYPE_CHECKING:
    from smarter.apps.llmclient.models import (
        LLMClient,
        LLMClientAPIKey,
        LLMClientCustomDomain,
        LLMClientExtensions,
        LLMClientGuardrails,
        LLMClientMCPClients,
        LLMClientPlugin,
    )


LLMClientApiDnsVerificationStatus = Literal["Verifying", "Not Verified", "Verified", "Failed"]
"""The choices of ``LLMClient.dns_verification_status``.

A test fails if the two differ.
"""

LLMClientApiTlsCertificateIssuanceStatus = Literal["No Certificate", "Requested", "Issued", "Failed"]
"""The choices of ``LLMClient.tls_certificate_issuance_status``.

A test fails if the two differ.
"""

LLMClientApiVerificationStatus = Literal["Not Verified", "Verifying", "Verified", "Failed"]
"""The choices of ``LLMClientCustomDomain.verification_status``.

A test fails if the two differ.
"""


class LLMClientApiOrmModel(AccountApiModel):
    """Base class of the models of LLMClient rows: their primary key and timestamps."""

    id: int = Field(..., description="The row's primary key.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")


class LLMClientApiExtension(LLMClientApiOrmModel):
    """An extension of an LLMClient: a :class:`smarter.apps.llmclient.models.LLMClientExtensions`."""

    name: str = Field(..., description="The extension's slug, e.g. weather.")
    extension: int = Field(..., description="LLMClientExtensions.extension: the Extension's id.")
    llmclient: int = Field(..., description="LLMClientExtensions.llmclient: the LLMClient's id.")

    @classmethod
    def from_model(cls, link: "LLMClientExtensions") -> "LLMClientApiExtension":
        """
        The contract's model of an extension of an LLMClient.

        :param link: The row, whose ``extension`` should be fetched with it.
        :type link: smarter.apps.llmclient.models.LLMClientExtensions
        :returns: The model.
        :rtype: LLMClientApiExtension
        """
        return cls(
            id=link.pk,
            created_at=link.created_at,
            updated_at=link.updated_at,
            name=link.extension.slug,
            extension=link.extension_id,  # type: ignore[attr-defined]
            llmclient=link.llmclient_id,  # type: ignore[attr-defined]
        )


class LLMClientApiPlugin(LLMClientApiOrmModel):
    """A plugin of an LLMClient: a :class:`smarter.apps.llmclient.models.LLMClientPlugin`, with the plugin's metadata."""

    plugin_meta: PluginApiPluginMeta = Field(..., description="LLMClientPlugin.plugin_meta: the plugin.")
    llmclient: int = Field(..., description="LLMClientPlugin.llmclient: the LLMClient's id.")

    @classmethod
    def from_model(cls, plugin: "LLMClientPlugin", user: object = None) -> "LLMClientApiPlugin":
        """
        The contract's model of a plugin of an LLMClient.

        :param plugin: The row, whose ``plugin_meta`` should be fetched with it.
        :type plugin: smarter.apps.llmclient.models.LLMClientPlugin
        :param user: The requesting user, for the plugin's ``canDelete``.
        :type user: object
        :returns: The model.
        :rtype: LLMClientApiPlugin
        """
        return cls(
            id=plugin.pk,
            created_at=plugin.created_at,
            updated_at=plugin.updated_at,
            plugin_meta=PluginApiPluginMeta.from_model(plugin.plugin_meta, user),
            llmclient=plugin.llmclient_id,  # type: ignore[attr-defined]
        )


class LLMClientApiPluginRef(AccountApiModel):
    """A plugin of an LLMClient, in the LLMClient's own response: the LLMClientPlugin's id, and the plugin's name."""

    id: int = Field(..., description="LLMClientPlugin.id.")
    name: str = Field(..., description="The plugin's name, PluginMeta.name.")

    @classmethod
    def from_model(cls, plugin: "LLMClientPlugin") -> "LLMClientApiPluginRef":
        """
        The contract's reference to a plugin of an LLMClient.

        :param plugin: The row, whose ``plugin_meta`` should be fetched with it.
        :type plugin: smarter.apps.llmclient.models.LLMClientPlugin
        :returns: The model.
        :rtype: LLMClientApiPluginRef
        """
        return cls(id=plugin.pk, name=plugin.plugin_meta.name)


class LLMClientApiMCPClientRef(AccountApiModel):
    """An MCPClient of an LLMClient, in the LLMClient's own response: the LLMClientMCPClients' id, and the MCPClient's name."""

    id: int = Field(..., description="LLMClientMCPClients.id.")
    name: str = Field(..., description="The MCPClient's name, MCPClient.name.")

    @classmethod
    def from_model(cls, link: "LLMClientMCPClients") -> "LLMClientApiMCPClientRef":
        """
        The contract's reference to an MCPClient of an LLMClient.

        :param link: The row, whose ``mcpclient`` should be fetched with it.
        :type link: smarter.apps.llmclient.models.LLMClientMCPClients
        :returns: The model.
        :rtype: LLMClientApiMCPClientRef
        """
        return cls(id=link.pk, name=link.mcpclient.name)


class LLMClientApiGuardrailRef(AccountApiModel):
    """A Guardrail of an LLMClient, in the LLMClient's own response: the LLMClientGuardrails' id, and the Guardrail's name."""

    id: int = Field(..., description="LLMClientGuardrails.id.")
    name: str = Field(..., description="The Guardrail's name, Guardrail.name.")

    @classmethod
    def from_model(cls, link: "LLMClientGuardrails") -> "LLMClientApiGuardrailRef":
        """
        The contract's reference to a Guardrail of an LLMClient.

        :param link: The row, whose ``guardrail`` should be fetched with it.
        :type link: smarter.apps.llmclient.models.LLMClientGuardrails
        :returns: The model.
        :rtype: LLMClientApiGuardrailRef
        """
        return cls(id=link.pk, name=link.guardrail.name)


LLMClientApiToolKind = Literal["Extension", "Plugin", "MCPClient", "Guardrail"]
"""What adds a tool to an LLMClient's prompts: an extension, or the linked resource's manifest kind."""


class LLMClientApiTool(AccountApiModel):
    """Something that an LLMClient adds to a prompt: an extension, plugin, MCPClient or guardrail."""

    id: int = Field(..., description="The link row's id: LLMClientExtensions, LLMClientPlugin, ... .id.")
    name: str = Field(..., description="The extension's slug, or the linked resource's name.")
    kind: LLMClientApiToolKind = Field(..., description="Extension, or the linked resource's manifest kind.")


class LLMClientApiKey(LLMClientApiOrmModel):
    """An api key of an LLMClient: a :class:`smarter.apps.llmclient.models.LLMClientAPIKey`."""

    llmclient: int = Field(..., description="LLMClientAPIKey.llmclient: the LLMClient's id.")
    api_key: UUID = Field(
        ...,
        description="LLMClientAPIKey.api_key: the SmarterAuthToken's public key_id. Never the key, nor its digest.",
    )

    @classmethod
    def from_model(cls, api_key: "LLMClientAPIKey") -> "LLMClientApiKey":
        """
        The contract's model of an api key of an LLMClient.

        :param api_key: The row, whose ``api_key`` should be fetched with it.
        :type api_key: smarter.apps.llmclient.models.LLMClientAPIKey
        :returns: The model.
        :rtype: LLMClientApiKey
        """
        return cls(
            id=api_key.pk,
            created_at=api_key.created_at,
            updated_at=api_key.updated_at,
            llmclient=api_key.llmclient_id,  # type: ignore[attr-defined]
            api_key=api_key.api_key.key_id,
        )


class LLMClientApiCustomDomain(LLMClientApiOrmModel):
    """A custom domain of an LLMClient: a :class:`smarter.apps.llmclient.models.LLMClientCustomDomain`."""

    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user_profile: int = Field(..., description="The custom domain's owner: the UserProfile's id.")
    aws_hosted_zone_id: str = Field(..., description="The id of the domain's DNS zone, empty until it has one.")
    domain_name: str = Field(..., description="The domain, e.g. example.com.")
    verification_status: LLMClientApiVerificationStatus = Field(
        ..., description="Whether the platform has verified that it controls the domain's DNS."
    )
    verified_at: Optional[datetime] = Field(None, description="When the domain was verified.")
    verification_message: str = Field(..., description="The result of the last verification, for a person.")

    @classmethod
    def from_model(cls, custom_domain: "LLMClientCustomDomain") -> "LLMClientApiCustomDomain":
        """
        The contract's model of a custom domain.

        :param custom_domain: The row.
        :type custom_domain: smarter.apps.llmclient.models.LLMClientCustomDomain
        :returns: The model.
        :rtype: LLMClientApiCustomDomain
        """
        return cls(
            id=custom_domain.pk,
            created_at=custom_domain.created_at,
            updated_at=custom_domain.updated_at,
            name=custom_domain.name,
            description=custom_domain.description,
            version=custom_domain.version,
            annotations=custom_domain.annotations,
            user_profile=custom_domain.user_profile_id,  # type: ignore[attr-defined]
            aws_hosted_zone_id=custom_domain.aws_hosted_zone_id,
            domain_name=custom_domain.domain_name,
            verification_status=custom_domain.verification_status,  # type: ignore[arg-type]
            verified_at=custom_domain.verified_at,
            verification_message=custom_domain.verification_message,
        )


class LLMClientApiLLMClient(LLMClientApiOrmModel):
    """
    An LLMClient: a :class:`smarter.apps.llmclient.models.LLMClient`, with its related rows and its urls.

    Its ``extensions``, ``plugins``, ``custom_domains`` and ``api_keys`` are inline, and its urls and
    hosts are computed, as the LLMClient's properties compute them for the platform that serves the
    request.
    """

    hashed_id: str = Field(..., description="The LLMClient's hashed id, e.g. rMTAwMDAwNgx, which its urls use.")
    name: str = Field(..., description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    user_profile: AccountApiUserProfile = Field(..., description="The LLMClient's owner.")
    can_delete: bool = Field(
        ...,
        description="Whether the requesting user may delete the LLMClient now: they own it, and nothing depends on it.",
    )
    extensions: list[LLMClientApiExtension] = Field(..., description="The LLMClient's extensions.")
    plugins: list[LLMClientApiPluginRef] = Field(..., description="The LLMClient's plugins.")
    mcpclients: list[LLMClientApiMCPClientRef] = Field(..., description="The LLMClient's MCPClients.")
    guardrails: list[LLMClientApiGuardrailRef] = Field(..., description="The LLMClient's guardrails.")
    tools: list[LLMClientApiTool] = Field(
        ...,
        description="Everything that the LLMClient adds to a prompt: its extensions, plugins, MCPClients and "
        "guardrails, in that order.",
    )
    custom_domains: list[LLMClientApiCustomDomain] = Field(
        ..., description="The LLMClient's custom domain, as a list of none or one."
    )
    api_keys: list[LLMClientApiKey] = Field(..., description="The LLMClient's api keys.")
    rfc1034_compliant_name: Optional[str] = Field(None, description="The name, as a DNS label.")
    default_system_role: Optional[str] = Field(
        None, description="The system prompt of a new chat session, with the current date and time."
    )
    base_api_domain: Optional[str] = Field(None, description="The platform's api domain, e.g. api.example.com.")
    base_default_host: Optional[str] = Field(None, description="The account's host under the api domain.")
    default_host: Optional[str] = Field(None, description="The LLMClient's host, once deployed.")
    default_url: Optional[str] = Field(None, description="The LLMClient's url, once deployed.")
    custom_host: Optional[str] = Field(None, description="The LLMClient's host on its custom domain, if any.")
    custom_url: Optional[str] = Field(None, description="The LLMClient's url on its custom domain, if any.")
    sandbox_host: Optional[str] = Field(None, description="The platform's host, which serves undeployed LLMClients.")
    sandbox_url: Optional[str] = Field(None, description="The LLMClient's page in the web console's workbench.")
    manifest_url: Optional[str] = Field(None, description="The url of the LLMClient's manifest in the web console.")
    hostname: Optional[str] = Field(None, description="The host that serves the LLMClient now.")
    url: Optional[str] = Field(None, description="The url that serves the LLMClient now.")
    url_llmclient: Optional[str] = Field(None, description="Where to send prompts: the chat api's prompt url.")
    url_chat_config: Optional[str] = Field(None, description="The chat api's configuration url.")
    url_chatapp: Optional[str] = Field(None, description="The LLMClient's chat page.")
    ready: bool = Field(..., description="Whether the LLMClient can be prompted.")
    is_authentication_required: bool = Field(..., description="Whether prompting the LLMClient requires an api key.")
    deployed: Optional[bool] = Field(None, description="LLMClient.deployed: whether it is served on its own host.")
    provider: Optional[str] = Field(None, description="LLMClient.provider: the LLM provider, e.g. openai.")
    default_model: Optional[str] = Field(None, description="LLMClient.default_model.")
    default_temperature: Optional[float] = Field(None, description="LLMClient.default_temperature.")
    default_max_tokens: Optional[int] = Field(None, description="LLMClient.default_max_tokens.")
    app_name: Optional[str] = Field(None, description="LLMClient.app_name.")
    app_assistant: Optional[str] = Field(None, description="LLMClient.app_assistant: the assistant's name.")
    app_welcome_message: Optional[str] = Field(None, description="LLMClient.app_welcome_message.")
    app_example_prompts: Optional[list[str]] = Field(None, description="LLMClient.app_example_prompts.")
    app_placeholder: Optional[str] = Field(None, description="LLMClient.app_placeholder.")
    app_info_url: Optional[str] = Field(None, description="LLMClient.app_info_url.")
    app_file_attachment: Optional[bool] = Field(None, description="LLMClient.app_file_attachment.")
    styles: Optional[dict[str, JsonValue]] = Field(None, description="LLMClient.styles: the chat's CSS styles.")
    allowed_origins: list[str] = Field(..., description="LLMClient.allowed_origins: the CORS origins of its pages.")
    dns_verification_status: Optional[LLMClientApiDnsVerificationStatus] = Field(
        None, description="LLMClient.dns_verification_status."
    )
    tls_certificate_issuance_status: Optional[LLMClientApiTlsCertificateIssuanceStatus] = Field(
        None, description="LLMClient.tls_certificate_issuance_status."
    )
    subdomain: Optional[int] = Field(None, description="LLMClient.subdomain: the Route53 record's id, if any.")
    custom_domain: Optional[int] = Field(None, description="LLMClient.custom_domain: the custom domain's id, if any.")

    @classmethod
    def from_model(cls, llmclient: "LLMClient", user: object = None) -> "LLMClientApiLLMClient":
        """
        The contract's model of an LLMClient.

        :param llmclient: The row, whose ``user_profile`` should be fetched with it.
        :type llmclient: smarter.apps.llmclient.models.LLMClient
        :param user: The requesting user, for ``can_delete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: LLMClientApiLLMClient
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.llmclient.manifest.models.llmclient.const import (
            MANIFEST_KIND as LLMCLIENT_KIND,
        )
        from smarter.apps.llmclient.models import (
            LLMClientAPIKey,
            LLMClientCustomDomain,
            LLMClientExtensions,
            LLMClientGuardrails,
            LLMClientMCPClients,
            LLMClientPlugin,
        )

        extensions = [
            LLMClientApiExtension.from_model(row)
            for row in LLMClientExtensions.objects.filter(llmclient=llmclient)
            .select_related("extension")
            .order_by("extension__slug")
        ]
        plugins = [
            LLMClientApiPluginRef.from_model(row)
            for row in LLMClientPlugin.objects.filter(llmclient=llmclient).select_related("plugin_meta")
        ]
        mcpclients = [
            LLMClientApiMCPClientRef.from_model(row)
            for row in LLMClientMCPClients.objects.filter(llmclient=llmclient).select_related("mcpclient")
        ]
        guardrails = [
            LLMClientApiGuardrailRef.from_model(row)
            for row in LLMClientGuardrails.objects.filter(llmclient=llmclient).select_related("guardrail")
        ]
        tools = [
            LLMClientApiTool(id=item.id, name=item.name, kind=kind)
            for kind, items in (
                ("Extension", extensions),
                ("Plugin", plugins),
                ("MCPClient", mcpclients),
                ("Guardrail", guardrails),
            )
            for item in items
            if item.name
        ]
        custom_domains = (
            LLMClientCustomDomain.objects.filter(id=llmclient.custom_domain_id)  # type: ignore[attr-defined]
            if llmclient.custom_domain_id  # type: ignore[attr-defined]
            else LLMClientCustomDomain.objects.none()
        )
        return cls(
            id=llmclient.pk,
            hashed_id=llmclient.hashed_id,
            created_at=llmclient.created_at,
            updated_at=llmclient.updated_at,
            name=llmclient.name,
            description=llmclient.description,
            version=llmclient.version,
            tags=[tag.name for tag in llmclient.tags.all()],
            annotations=llmclient.annotations,
            user_profile=AccountApiUserProfile.from_model(llmclient.user_profile),
            can_delete=user_can_delete(llmclient, LLMCLIENT_KIND, user),
            extensions=extensions,
            plugins=plugins,
            mcpclients=mcpclients,
            guardrails=guardrails,
            tools=tools,
            custom_domains=[LLMClientApiCustomDomain.from_model(row) for row in custom_domains],
            api_keys=[
                LLMClientApiKey.from_model(row)
                for row in LLMClientAPIKey.objects.filter(llmclient=llmclient).select_related("api_key")
            ],
            rfc1034_compliant_name=llmclient.rfc1034_compliant_name,
            default_system_role=llmclient.default_system_role_enhanced,
            base_api_domain=llmclient.base_api_domain,
            base_default_host=llmclient.base_default_host,
            default_host=llmclient.default_host,
            default_url=llmclient.default_url,
            custom_host=llmclient.custom_host,
            custom_url=llmclient.custom_url,
            sandbox_host=llmclient.sandbox_host,
            sandbox_url=llmclient.sandbox_url,
            manifest_url=llmclient.manifest_url,
            hostname=llmclient.hostname,
            url=llmclient.url,
            url_llmclient=llmclient.url_llmclient,
            url_chat_config=llmclient.url_chat_config,
            url_chatapp=llmclient.url_chatapp,
            ready=llmclient.ready,
            is_authentication_required=llmclient.is_authentication_required,
            deployed=llmclient.deployed,
            provider=llmclient.provider,
            default_model=llmclient.default_model,
            default_temperature=llmclient.default_temperature,
            default_max_tokens=llmclient.default_max_tokens,
            app_name=llmclient.app_name,
            app_assistant=llmclient.app_assistant,
            app_welcome_message=llmclient.app_welcome_message,
            app_example_prompts=llmclient.app_example_prompts,
            app_placeholder=llmclient.app_placeholder,
            app_info_url=llmclient.app_info_url,
            app_file_attachment=llmclient.app_file_attachment,
            styles=llmclient.styles,
            allowed_origins=llmclient.allowed_origins,
            dns_verification_status=llmclient.dns_verification_status,  # type: ignore[arg-type]
            tls_certificate_issuance_status=llmclient.tls_certificate_issuance_status,  # type: ignore[arg-type]
            subdomain=llmclient.subdomain_id,  # type: ignore[attr-defined]
            custom_domain=llmclient.custom_domain_id,  # type: ignore[attr-defined]
        )


LLMCLIENT_API_MODELS = (
    LLMClientApiLLMClient,
    LLMClientApiPlugin,
    LLMClientApiExtension,
    LLMClientApiKey,
    LLMClientApiCustomDomain,
)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes.

Their dependencies are included with them.
"""

__all__ = [
    "LLMCLIENT_API_MODELS",
    "LLMClientApiCustomDomain",
    "LLMClientApiDnsVerificationStatus",
    "LLMClientApiExtension",
    "LLMClientApiGuardrailRef",
    "LLMClientApiKey",
    "LLMClientApiLLMClient",
    "LLMClientApiMCPClientRef",
    "LLMClientApiOrmModel",
    "LLMClientApiPlugin",
    "LLMClientApiPluginRef",
    "LLMClientApiTool",
    "LLMClientApiToolKind",
    "LLMClientApiTlsCertificateIssuanceStatus",
    "LLMClientApiVerificationStatus",
]
