# -*- coding: utf-8 -*-
"""PluginMeta serializers."""
from rest_framework import serializers
from taggit.models import TaggedItem

from smarter.apps.account.serializers import UserProfileSerializer

from .models import PluginData, PluginMeta, PluginPrompt, PluginSelector


class TaggedItemSerializer(serializers.ModelSerializer):
    """TaggedItem model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = TaggedItem
        fields = ["tag"]


class PluginMetaSerializer(serializers.ModelSerializer):
    """PluginMeta model serializer."""

    tags = TaggedItemSerializer(many=True, read_only=True)
    author = UserProfileSerializer(read_only=True)

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginMeta
        fields = ["name", "description", "version", "author", "tags"]


class PluginSelectorSerializer(serializers.ModelSerializer):
    """PluginSelector model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginSelector
        fields = ["directive"]


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
