# -*- coding: utf-8 -*-
"""Plugin views."""
from rest_framework import viewsets
from rest_framework.exceptions import ValidationError

from .models import (
    Plugin,
    PluginFunction,
    PluginPrompt,
    PluginSelector,
    PluginSelectorSearchStrings,
)
from .serializers import (
    PluginFunctionSerializer,
    PluginPromptSerializer,
    PluginSelectorSearchStringsSerializer,
    PluginSelectorSerializer,
    PluginSerializer,
)


class PluginViewSet(viewsets.ModelViewSet):
    """Plugin model view set."""

    serializer_class = PluginSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned PluginSelectors to a given Plugin,
        by filtering against a `plugin_id` query parameter in the URL.
        """
        queryset = Plugin.objects.all()
        account_id = self.request.query_params.get("account_id", None)
        if account_id is not None:
            queryset = queryset.filter(account_id=account_id)
        else:
            raise ValidationError({"account_id": "This field is required."})
        return queryset


class PluginSelectorViewSet(viewsets.ModelViewSet):
    """PluginSelector model view set."""

    serializer_class = PluginSelectorSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned PluginSelectors to a given Plugin,
        by filtering against a `plugin_id` query parameter in the URL.
        """
        queryset = PluginSelector.objects.all()
        plugin_id = self.request.query_params.get("plugin_id", None)
        if plugin_id is not None:
            queryset = queryset.filter(plugin_id=plugin_id)
        else:
            raise ValidationError({"plugin_id": "This field is required."})
        return queryset


class PluginSelectorSearchStringsViewSet(viewsets.ModelViewSet):
    """PluginSelectorSearchStrings model view set."""

    queryset = PluginSelectorSearchStrings.objects.all()
    serializer_class = PluginSelectorSearchStringsSerializer


class PluginPromptViewSet(viewsets.ModelViewSet):
    """PluginPrompt model view set."""

    serializer_class = PluginPromptSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned PluginSelectors to a given Plugin,
        by filtering against a `plugin_id` query parameter in the URL.
        """
        queryset = PluginPrompt.objects.all()
        plugin_id = self.request.query_params.get("plugin_id", None)
        if plugin_id is not None:
            queryset = queryset.filter(plugin_id=plugin_id)
        else:
            raise ValidationError({"plugin_id": "This field is required."})
        return queryset


class PluginFunctionViewSet(viewsets.ModelViewSet):
    """PluginFunction model view set."""

    serializer_class = PluginFunctionSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned PluginSelectors to a given Plugin,
        by filtering against a `plugin_id` query parameter in the URL.
        """
        queryset = PluginFunction.objects.all()
        plugin_id = self.request.query_params.get("plugin_id", None)
        if plugin_id is not None:
            queryset = queryset.filter(plugin_id=plugin_id)
        else:
            raise ValidationError({"plugin_id": "This field is required."})
        return queryset
