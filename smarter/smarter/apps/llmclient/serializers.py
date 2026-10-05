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
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientCustomDomainDNS,
    LLMClientFunctions,
    LLMClientPlugin,
    LLMClientRequests,
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
    """
    Serializer for the smarter.apps.prompt.views.PromptConfigView.

    which should not be camelCased.
    """

    url_llmclient = serializers.ReadOnlyField()
    user_profile = UserProfileSerializer()
    default_system_role = serializers.SerializerMethodField()
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


class LLMClientAPIKeySerializer(SmarterCamelCaseSerializer):

    class Meta:
        model = LLMClientAPIKey
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields


class LLMClientCustomDomainSerializer(SmarterCamelCaseSerializer):

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
    A custom domain: the resource's metadata and owner, the domain, the.

    llmclient that it serves, and its DNS records. Used by the Custom Domain
    list in the web console, and by the CustomDomain broker's ``get``.
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


class LLMClientFunctionsSerializer(SmarterCamelCaseSerializer):

    class Meta:
        model = LLMClientFunctions
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
    functions = serializers.SerializerMethodField()
    plugins = serializers.SerializerMethodField()
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

    def get_functions(self, obj: LLMClient):
        qs = LLMClientFunctions.objects.filter(llmclient=obj)
        return LLMClientFunctionsSerializer(qs, many=True).data

    def get_plugins(self, obj: LLMClient):
        qs = LLMClientPlugin.objects.filter(llmclient=obj)
        return LLMClientPluginMiniSerializer(qs, many=True).data

    def get_custom_domains(self, obj: LLMClient):
        qs = LLMClientCustomDomain.objects.filter(id=obj.custom_domain.id) if obj.custom_domain else LLMClientCustomDomain.objects.none()  # type: ignore
        return LLMClientCustomDomainSerializer(qs, many=True).data

    def get_api_keys(self, obj: LLMClient):
        qs = LLMClientAPIKey.objects.filter(llmclient=obj)
        return LLMClientAPIKeySerializer(qs, many=True).data

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
    "LLMClientFunctionsSerializer",
    "LLMClientCustomDomainSerializer",
    "LLMClientCustomDomainListSerializer",
]
