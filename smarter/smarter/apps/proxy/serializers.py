"""Serializers for the Proxy app."""

from rest_framework import serializers

from smarter.apps.account.serializers import MetaDataWithOwnershipModelSerializer
from smarter.apps.proxy.manifest.models.proxy.const import MANIFEST_KIND as PROXY_KIND
from smarter.apps.proxy.models import Proxy


class ProxySerializer(MetaDataWithOwnershipModelSerializer):
    """
    Serializer for the smarter.apps.proxy.models.Proxy model.

    Used by the web console's list view and the ``smarter get proxies`` CLI command. The API key
    is rendered as its Secret's name, never its value.
    """

    provider_name = serializers.SerializerMethodField()
    api_key_secret_name = serializers.SerializerMethodField()
    upstream_url = serializers.SerializerMethodField()
    url = serializers.SerializerMethodField()
    manifest_url = serializers.SerializerMethodField()

    class Meta:
        model = Proxy
        kind = PROXY_KIND
        fields = "__all__"

    def get_fields(self):
        fields = super().get_fields()
        for field in fields.values():
            field.read_only = True
        return fields

    def get_provider_name(self, obj: Proxy) -> str:
        """The name of the Provider whose API the Proxy forwards to."""
        return obj.provider.name

    def get_api_key_secret_name(self, obj: Proxy) -> str | None:
        """The name of the Secret whose API key is added to requests: the Proxy's, else the Provider's."""
        return obj.secret_name

    def get_upstream_url(self, obj: Proxy) -> str:
        """The base URL of the provider's API, to which requests are forwarded."""
        return obj.upstream_base_url

    def get_url(self, obj: Proxy) -> str:
        """The path of the Proxy's passthrough endpoint, e.g. /api/v1/proxy/openai/."""
        return obj.url

    def get_manifest_url(self, obj: Proxy) -> str:
        """The URL of the Proxy's detail view, which renders its manifest."""
        return obj.manifest_url


__all__ = ["ProxySerializer"]
