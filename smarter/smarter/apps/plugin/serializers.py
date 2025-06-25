"""PluginMeta serializers."""

from rest_framework import serializers
from taggit.models import Tag

from smarter.apps.account.serializers import (
    AccountMiniSerializer,
    SecretSerializer,
    UserProfileSerializer,
)
from smarter.apps.plugin.models import (
    ApiConnection,
    PluginDataApi,
    PluginDataSql,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
    SqlConnection,
)
from smarter.lib.drf.serializers import SmarterCamelCaseSerializer

from .manifest.enum import (
    SAMPluginCommonMetadataClassValues,
    SAMPluginCommonSpecSelectorKeyDirectiveValues,
)


class TagListSerializerField(serializers.ListField):
    """Tag list serializer."""

    child = serializers.CharField()

    def to_representation(self, data):
        if hasattr(data, "all"):
            tags = data.all()
        else:
            tags = data
        return [str(tag) for tag in tags]

    def to_internal_value(self, data):
        return [Tag.objects.get_or_create(name=name)[0] for name in data]


class PluginMetaSerializer(SmarterCamelCaseSerializer):
    """PluginMeta model serializer."""

    tags = TagListSerializerField()
    author = UserProfileSerializer(read_only=True)
    account = AccountMiniSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginMeta
        fields = ["name", "account", "description", "plugin_class", "version", "author", "tags"]


class PluginSelectorSerializer(SmarterCamelCaseSerializer):
    """PluginSelector model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginSelector
        fields = ["directive", SAMPluginCommonSpecSelectorKeyDirectiveValues.SEARCHTERMS.value]


class PluginPromptSerializer(SmarterCamelCaseSerializer):
    """PluginPrompt model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginPrompt
        fields = ["provider", "system_role", "model", "temperature", "max_tokens"]


class PluginStaticSerializer(SmarterCamelCaseSerializer):
    """PluginDataStatic model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginDataStatic
        fields = ["description", "static_data"]


class SqlConnectionSerializer(SmarterCamelCaseSerializer):
    """SqlConnection model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SqlConnection
        fields = [
            "name",
            "description",
            "hostname",
            "port",
            "database",
            "username",
            "password",
            "proxy_protocol",
            "proxy_host",
            "proxy_port",
            "proxy_username",
            "proxy_password",
        ]


class PluginSqlSerializer(SmarterCamelCaseSerializer):
    """PluginDataSql model serializer."""

    connection = serializers.SlugRelatedField(slug_field="name", queryset=SqlConnection.objects.all())

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginDataSql
        fields = [
            "connection",
            "description",
            "parameters",
            "sql_query",
            "test_values",
            "limit",
        ]


class ApiConnectionSerializer(SmarterCamelCaseSerializer):
    """ApiConnection model serializer."""

    account = AccountMiniSerializer(read_only=True)
    api_key = SecretSerializer(read_only=True)
    proxy_password = SecretSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = ApiConnection
        fields = [
            "account",
            "name",
            "description",
            "base_url",
            "api_key",
            "auth_method",
            "timeout",
            "proxy_protocol",
            "proxy_host",
            "proxy_port",
            "proxy_username",
            "proxy_password",
        ]


class PluginApiSerializer(SmarterCamelCaseSerializer):
    """PluginDataApi model serializer."""

    connection = serializers.SlugRelatedField(slug_field="name", queryset=ApiConnection.objects.all())

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginDataApi
        fields = [
            "connection",
            "description",
            "parameters",
            "url",
            "method",
            "headers",
            "params",
            "data",
            "auth_type",
            "username",
            "password",
        ]
