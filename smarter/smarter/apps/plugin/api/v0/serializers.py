# -*- coding: utf-8 -*-
"""PluginMeta serializers."""
from rest_framework import serializers
from taggit.models import Tag

from smarter.apps.account.serializers import AccountSerializer, UserProfileSerializer
from smarter.apps.plugin.models import (
    PluginData,
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
    # tags = serializers.StringRelatedField(many=True)
    author = UserProfileSerializer(read_only=True)
    account = AccountSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginMeta
        fields = ["name", "account", "description", "version", "author", "tags"]


class PluginSelectorSerializer(serializers.ModelSerializer):
    """PluginSelector model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginSelector
        fields = ["directive", "search_terms"]


class PluginPromptSerializer(serializers.ModelSerializer):
    """PluginPrompt model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginPrompt
        fields = ["system_role", "model", "temperature", "max_tokens"]


class PluginDataSerializer(serializers.ModelSerializer):
    """PluginData model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginData
        fields = ["description", "return_data"]
