"""PluginMeta serializers."""

from rest_framework import serializers
from taggit.models import Tag

from smarter.apps.account.serializers import AccountSerializer, UserProfileSerializer
from smarter.apps.plugin.models import (
    PluginDataSql,
    PluginDataSqlConnection,
    PluginDataStatic,
    PluginMeta,
    PluginPrompt,
    PluginSelector,
)


class TagListSerializerField(serializers.ListField):
    """Tag list serializer."""

    child = serializers.CharField()

    def to_representation(self, data):
        return [tag.name for tag in data.all()]

    def to_internal_value(self, data):
        return [Tag.objects.get_or_create(name=name)[0] for name in data]


class PluginMetaSerializer(serializers.ModelSerializer):
    """PluginMeta model serializer."""

    tags = TagListSerializerField()
    author = UserProfileSerializer(read_only=True)
    account = AccountSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginMeta
        fields = ["name", "account", "description", "plugin_class", "version", "author", "tags"]

    def to_representation(self, instance):
        """Convert `username` to `userName`."""
        representation = super().to_representation(instance)
        new_representation = {}
        for key in representation.keys():
            new_key = "".join(word.capitalize() for word in key.split("_"))
            new_key = new_key[0].lower() + new_key[1:]
            new_representation[new_key] = representation[key]
        return new_representation


class PluginSelectorSerializer(serializers.ModelSerializer):
    """PluginSelector model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginSelector
        fields = ["directive", "search_terms"]

    def to_representation(self, instance):
        """Convert `username` to `userName`."""
        representation = super().to_representation(instance)
        representation["searchTerms"] = representation.pop("search_terms")
        return representation


class PluginPromptSerializer(serializers.ModelSerializer):
    """PluginPrompt model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginPrompt
        fields = ["system_role", "model", "temperature", "max_tokens"]

    def to_representation(self, instance):
        """Convert `username` to `userName`."""
        representation = super().to_representation(instance)
        new_representation = {}
        for key in representation.keys():
            new_key = "".join(word.capitalize() for word in key.split("_"))
            new_key = new_key[0].lower() + new_key[1:]
            if isinstance(representation[key], str):
                new_representation[new_key] = representation[key].strip()
            else:
                new_representation[new_key] = representation[key]
        return new_representation


class PluginDataStaticSerializer(serializers.ModelSerializer):
    """PluginDataStatic model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginDataStatic
        fields = ["description", "static_data"]

    def to_representation(self, instance):
        """Convert `username` to `userName`."""
        representation = super().to_representation(instance)
        new_representation = {}
        for key in representation.keys():
            new_key = "".join(word.capitalize() for word in key.split("_"))
            new_key = new_key[0].lower() + new_key[1:]
            if isinstance(representation[key], str):
                new_representation[new_key] = representation[key].strip()
            else:
                new_representation[new_key] = representation[key]
        return new_representation


class PluginDataSqlConnectionSerializer(serializers.ModelSerializer):
    """PluginDataSql model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginDataSqlConnection
        fields = [
            "name",
            "description",
            "hostname",
            "port",
            "database",
            "username",
            "password",
            "proxy_host",
            "proxy_port",
            "proxy_username",
            "proxy_password",
        ]

    def to_representation(self, instance):
        """Convert `username` to `userName`."""
        representation = super().to_representation(instance)
        new_representation = {}
        for key in representation.keys():
            new_key = "".join(word.capitalize() for word in key.split("_"))
            new_key = new_key[0].lower() + new_key[1:]
            if isinstance(representation[key], str):
                new_representation[new_key] = representation[key].strip()
            else:
                new_representation[new_key] = representation[key]
        return new_representation


class PluginDataSqlSerializer(serializers.ModelSerializer):
    """PluginDataSql model serializer."""

    connection = serializers.SlugRelatedField(slug_field="name", queryset=PluginDataSqlConnection.objects.all())

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

    def to_representation(self, instance):
        """Convert `username` to `userName`."""
        representation = super().to_representation(instance)
        new_representation = {}
        for key in representation.keys():
            new_key = "".join(word.capitalize() for word in key.split("_"))
            new_key = new_key[0].lower() + new_key[1:]
            if isinstance(representation[key], str):
                new_representation[new_key] = representation[key].strip()
            else:
                new_representation[new_key] = representation[key]
        return new_representation
