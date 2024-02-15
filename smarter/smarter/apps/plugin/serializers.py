# -*- coding: utf-8 -*-
"""Plugin serializers."""
from rest_framework import serializers

from .models import Plugin


class PluginModelSerializer(serializers.ModelSerializer):
    """Plugin model serializer."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Plugin
        fields = ["_yaml", "tags"]
