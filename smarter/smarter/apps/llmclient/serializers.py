# pylint: disable=missing-class-docstring,W0212
"""LLMClient serializers."""

from rest_framework import serializers

from smarter.apps.account.serializers import (
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
)
from smarter.apps.llmclient.manifest.models.custom_domain.const import (
    MANIFEST_KIND as CUSTOM_DOMAIN_KIND,
)
from smarter.apps.llmclient.manifest.models.llmclient.const import (
    MANIFEST_KIND as LLMCLIENT_KIND,
)
from smarter.apps.llmtool.manifest.models.common.plugin.const import (
    MANIFEST_KIND as PLUGIN_KIND,
)
from smarter.apps.llmtool.serializers import PluginMetaSerializer
from smarter.apps.mcpclient.manifest.models.mcpclient.const import (
    MANIFEST_KIND as MCPCLIENT_KIND,
)
from smarter.lib.django.serializers import related_rows
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
    LLMClientExtensions,
    LLMClientGuardrails,
    LLMClientMCPClients,
    LLMClientPlugin,
    LLMClientRequests,
    get_cached_llmclient_tool_counts,
)


class LLMClientRequestsSerializer(serializers.ModelSerializer):
    """Serializer for the LLMClientRequests model."""

    # pylint: disable=C0115
    class Meta:
        model = LLMClientRequests
        fields = (
            "id",
            "created_at",
            "updated_at",
            "request",
            "is_aggregation",
        )


class LLMClientConfigSerializer(serializers.ModelSerializer):
    """Serializer for the smarter.apps.prompt.views.PromptConfigView which should not be camelCased."""

    url_llmclient = serializers.ReadOnlyField()
    user_profile = UserProfileSerializer()
    default_system_role = serializers.SerializerMethodField()
    total_tools = serializers.SerializerMethodField()
    annotations = serializers.JSONField()

    class Meta:
        model = LLMClient
        kind = LLMCLIENT_KIND
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_default_system_role(self, obj: LLMClient):
        return obj.default_system_role_enhanced

    def get_total_tools(self, obj: LLMClient) -> int:
        """
        The number of tools that the LLMClient adds to a prompt.

        Counted, and cached until the LLMClient's tools change, rather than serialized: Smarter Chat's
        configuration api reads it on every page load.

        :param obj: The LLMClient.
        :returns: The length of :meth:`LLMClientSerializer.get_tools`: its extensions, plugins and MCPClients.
        :rtype: int
        """
        return get_cached_llmclient_tool_counts(obj.id).total  # type: ignore[arg-type]


class LLMClientAPIKeySerializer(SmarterCamelCaseSerializer):
    """
    An api key of an LLMClient.

    ``api_key`` is the SmarterAuthToken's public key_id. The token's primary key is its digest, a hash
    of the key, which the api never returns.
    """

    api_key = serializers.UUIDField(source="api_key.key_id", read_only=True)

    class Meta:
        model = LLMClientAPIKey
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class LLMClientCustomDomainSerializer(SmarterCamelCaseSerializer):

    # annotations is a property of MetaDataModel, not a column, so "__all__" leaves it out.
    annotations = serializers.JSONField(required=False)

    class Meta:
        model = LLMClientCustomDomain
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class LLMClientCustomDomainListSerializer(MetaDataWithOwnershipModelSerializer):
    """
    A custom domain: the resource's metadata and owner, the domain, the llmclient that it serves, and its DNS records.

    Used by the Custom Domain list in the web console, and by the CustomDomain broker's ``get``.
    """

    user_profile = UserProfileSerializer(read_only=True)
    manifest_url = serializers.SerializerMethodField()
    llmclient = serializers.SerializerMethodField()
    dns_records = serializers.SerializerMethodField()

    # pylint: disable=missing-class-docstring
    class Meta(MetaDataWithOwnershipModelSerializer.Meta):
        model = LLMClientCustomDomain
        kind = CUSTOM_DOMAIN_KIND
        fields = [
            "id",
            "created_at",
            "updated_at",
            "name",
            "user_profile",
            "description",
            "version",
            "annotations",
            "tags",
            "domain_name",
            "aws_hosted_zone_id",
            "verification_status",
            "verified_at",
            "verification_message",
            "manifest_url",
            "llmclient",
            "dns_records",
        ]
        read_only_fields = fields

    def get_manifest_url(self, obj: LLMClientCustomDomain) -> str:
        """The URL of the custom domain's detail view, which renders its manifest."""
        # pylint: disable=C0415
        from django.urls import reverse

        from .urls import LLMClientReverseNames

        return reverse(
            f"{LLMClientReverseNames.namespace}:{LLMClientReverseNames.custom_domain_detailview}",
            kwargs={"hashed_id": obj.hashed_id},
        )

    def get_llmclient(self, obj: LLMClientCustomDomain):
        """The llmclient that the domain serves, or None if no llmclient uses it."""
        llmclient = getattr(obj, "llmclient", None)
        if llmclient is None:
            return None
        return {
            "id": llmclient.id,
            "name": llmclient.name,
            "deployed": llmclient.deployed,
            "url": llmclient.custom_url,
            "sandbox_url": llmclient.sandbox_url,
            "manifest_url": llmclient.manifest_url,
            "owner": llmclient.user_profile.user.username,
        }

    def get_dns_records(self, obj: LLMClientCustomDomain):
        return [
            {
                "name": record.record_name,
                "type": record.record_type,
                "value": record.record_value,
                "ttl": record.record_ttl,
            }
            for record in LLMClientCustomDomainDNS.objects.filter(custom_domain=obj).order_by("record_name")
        ]


class LLMClientPluginSerializer(SmarterCamelCaseSerializer):
    plugin_meta = PluginMetaSerializer()

    class Meta:
        model = LLMClientPlugin
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class LLMClientPluginMiniSerializer(SmarterCamelCaseSerializer):

    # pylint: disable=C0115
    class Meta:
        model = LLMClientPlugin
        fields = ("id", "name")

    name = serializers.CharField(source="plugin_meta.name", read_only=True)


class LLMClientMCPClientMiniSerializer(SmarterCamelCaseSerializer):
    """An MCPClient of an LLMClient: the link's id, and the MCPClient's name."""

    # pylint: disable=C0115
    class Meta:
        model = LLMClientMCPClients
        fields = ("id", "name")

    name = serializers.CharField(source="mcpclient.name", read_only=True)


class LLMClientGuardrailMiniSerializer(SmarterCamelCaseSerializer):
    """A Guardrail of an LLMClient: the link's id, and the Guardrail's name."""

    # pylint: disable=C0115
    class Meta:
        model = LLMClientGuardrails
        fields = ("id", "name")

    name = serializers.CharField(source="guardrail.name", read_only=True)


class LLMClientExtensionsSerializer(SmarterCamelCaseSerializer):
    """An Extension of an LLMClient: the link row, and the Extension's slug as its name."""

    name = serializers.CharField(source="extension.slug", read_only=True)

    class Meta:
        model = LLMClientExtensions
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class LLMClientSerializer(MetaDataWithOwnershipModelSerializer):
    hashed_id = serializers.SerializerMethodField()
    url_llmclient = serializers.ReadOnlyField()
    user_profile = UserProfileSerializer()
    extensions = serializers.SerializerMethodField()
    plugins = serializers.SerializerMethodField()
    mcpclients = serializers.SerializerMethodField()
    guardrails = serializers.SerializerMethodField()
    tools = serializers.SerializerMethodField()
    custom_domains = serializers.SerializerMethodField()
    api_keys = serializers.SerializerMethodField()
    rfc1034_compliant_name = serializers.SerializerMethodField()
    default_system_role = serializers.SerializerMethodField()
    base_api_domain = serializers.SerializerMethodField()
    base_default_host = serializers.SerializerMethodField()
    default_host = serializers.SerializerMethodField()
    default_url = serializers.SerializerMethodField()
    custom_host = serializers.SerializerMethodField()
    custom_url = serializers.SerializerMethodField()
    sandbox_host = serializers.SerializerMethodField()
    sandbox_url = serializers.SerializerMethodField()
    manifest_url = serializers.SerializerMethodField()
    hostname = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    url_llmclient = serializers.SerializerMethodField()
    url_chat_config = serializers.SerializerMethodField()
    url_chatapp = serializers.SerializerMethodField()
    ready = serializers.SerializerMethodField()
    is_authentication_required = serializers.SerializerMethodField()

    class Meta:
        model = LLMClient
        kind = LLMCLIENT_KIND
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_extensions(self, obj: LLMClient):
        rows = related_rows(obj, "llmclientextensions_set", LLMClientExtensions, "extension")
        rows.sort(key=lambda row: row.extension.slug)
        return LLMClientExtensionsSerializer(rows, many=True).data

    def get_plugins(self, obj: LLMClient):
        rows = related_rows(obj, "llmclientplugin_set", LLMClientPlugin, "plugin_meta")
        return LLMClientPluginMiniSerializer(rows, many=True).data

    def get_mcpclients(self, obj: LLMClient):
        rows = related_rows(obj, "llmclientmcpclients_set", LLMClientMCPClients, "mcpclient")
        return LLMClientMCPClientMiniSerializer(rows, many=True).data

    def get_guardrails(self, obj: LLMClient):
        rows = related_rows(obj, "llmclientguardrails_set", LLMClientGuardrails, "guardrail")
        return LLMClientGuardrailMiniSerializer(rows, many=True).data

    def get_tools(self, obj: LLMClient):
        """
        The tools that the LLMClient offers the LLM: its extensions, plugins and MCPClients.

        Guardrails are left out: they constrain a prompt, but the LLM can't call them.

        :param obj: The LLMClient.
        :returns: One ``{"id", "name", "kind"}`` per extension, plugin and MCPClient, in that
            order. ``id`` is the link row's id, and ``kind`` is ``Extension`` or the linked resource's
            manifest kind.
        :rtype: list[dict]
        """
        return [
            {"id": item["id"], "name": item["name"], "kind": kind}
            for kind, items in (
                ("Extension", self.get_extensions(obj)),
                (PLUGIN_KIND, self.get_plugins(obj)),
                (MCPCLIENT_KIND, self.get_mcpclients(obj)),
            )
            for item in items
            if item["name"]
        ]

    def get_custom_domains(self, obj: LLMClient):
        rows = [obj.custom_domain] if obj.custom_domain else []
        return LLMClientCustomDomainSerializer(rows, many=True).data

    def get_api_keys(self, obj: LLMClient):
        rows = related_rows(obj, "llmclientapikey_set", LLMClientAPIKey, "api_key")
        return LLMClientAPIKeySerializer(rows, many=True).data

    def get_hashed_id(self, obj: LLMClient):
        return obj.hashed_id

    def get_rfc1034_compliant_name(self, obj: LLMClient):
        return obj.rfc1034_compliant_name

    def get_default_system_role(self, obj: LLMClient):
        return obj.default_system_role_enhanced

    def get_base_api_domain(self, obj: LLMClient):
        return obj.base_api_domain

    def get_base_default_host(self, obj: LLMClient):
        return obj.base_default_host

    def get_default_host(self, obj: LLMClient):
        return obj.default_host

    def get_default_url(self, obj: LLMClient):
        return obj.default_url

    def get_custom_host(self, obj: LLMClient):
        return obj.custom_host

    def get_custom_url(self, obj: LLMClient):
        return obj.custom_url

    def get_sandbox_host(self, obj: LLMClient):
        return obj.sandbox_host

    def get_sandbox_url(self, obj: LLMClient):
        return obj.sandbox_url

    def get_manifest_url(self, obj: LLMClient):
        return obj.manifest_url

    def get_hostname(self, obj: LLMClient):
        return obj.hostname

    def get_url(self, obj: LLMClient):
        return obj.url

    def get_url_llmclient(self, obj: LLMClient):
        return obj.url_llmclient

    def get_url_chat_config(self, obj: LLMClient):
        return obj.url_chat_config

    def get_url_chatapp(self, obj: LLMClient):
        return obj.url_chatapp

    def get_ready(self, obj: LLMClient):
        return obj.ready

    def get_is_authentication_required(self, obj: LLMClient):
        return obj.is_authentication_required


__all__ = [
    "LLMClientRequestsSerializer",
    "LLMClientSerializer",
    "LLMClientConfigSerializer",
    "LLMClientAPIKeySerializer",
    "LLMClientPluginSerializer",
    "LLMClientPluginMiniSerializer",
    "LLMClientMCPClientMiniSerializer",
    "LLMClientGuardrailMiniSerializer",
    "LLMClientExtensionsSerializer",
    "LLMClientCustomDomainSerializer",
    "LLMClientCustomDomainListSerializer",
]
