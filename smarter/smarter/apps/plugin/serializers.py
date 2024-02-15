# -*- coding: utf-8 -*-
"""Plugin serializers."""
from rest_framework import serializers

from .models import (
    Plugin,
    PluginFunction,
    PluginPrompt,
    PluginSelector,
    PluginSelectorSearchStrings,
)


class PluginSerializer(serializers.ModelSerializer):
    """Plugin model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Plugin
        fields = ["name", "description", "version", "author", "tags"]


class PluginSelectorSerializer(serializers.ModelSerializer):
    """PluginSelector model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginSelector
        fields = ["directive"]


class PluginSelectorSearchStringsSerializer(serializers.ModelSerializer):
    """PluginSelectorSearchStrings model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginSelectorSearchStrings
        fields = ["strings"]


class PluginPromptSerializer(serializers.ModelSerializer):
    """PluginPrompt model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginPrompt
        fields = ["system_prompt", "model", "temperature", "max_tokens"]


class PluginFunctionSerializer(serializers.ModelSerializer):
    """PluginFunction model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = PluginFunction
        fields = ["description", "yaml"]
