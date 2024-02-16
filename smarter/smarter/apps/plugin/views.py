# -*- coding: utf-8 -*-
"""PluginMeta views."""

from django.http import JsonResponse
from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.exceptions import ValidationError
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smarter.apps.account.models import UserProfile

from .models import PluginData, PluginMeta, PluginPrompt, PluginSelector
from .providers import AccountProvider, Plugin
from .serializers import (
    PluginDataSerializer,
    PluginMetaSerializer,
    PluginPromptSerializer,
    PluginSelectorSerializer,
)


class PluginViewSet(viewsets.ModelViewSet):
    """PluginMeta model view set."""

    serializer_class = PluginMetaSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned PluginSelectors to a given PluginMeta,
        by filtering against a `plugin_id` query parameter in the URL.
        """
        queryset = PluginMeta.objects.all()
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
        Optionally restricts the returned PluginSelectors to a given PluginMeta,
        by filtering against a `plugin_id` query parameter in the URL.
        """
        queryset = PluginSelector.objects.all()
        plugin_id = self.request.query_params.get("plugin_id", None)
        if plugin_id is not None:
            queryset = queryset.filter(plugin_id=plugin_id)
        else:
            raise ValidationError({"plugin_id": "This field is required."})
        return queryset


class PluginPromptViewSet(viewsets.ModelViewSet):
    """PluginPrompt model view set."""

    serializer_class = PluginPromptSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned PluginSelectors to a given PluginMeta,
        by filtering against a `plugin_id` query parameter in the URL.
        """
        queryset = PluginPrompt.objects.all()
        plugin_id = self.request.query_params.get("plugin_id", None)
        if plugin_id is not None:
            queryset = queryset.filter(plugin_id=plugin_id)
        else:
            raise ValidationError({"plugin_id": "This field is required."})
        return queryset


class PluginDataViewSet(viewsets.ModelViewSet):
    """PluginData model view set."""

    serializer_class = PluginDataSerializer

    def get_queryset(self):
        """
        Optionally restricts the returned PluginSelectors to a given PluginMeta,
        by filtering against a `plugin_id` query parameter in the URL.
        """
        queryset = PluginData.objects.all()
        plugin_id = self.request.query_params.get("plugin_id", None)
        if plugin_id is not None:
            queryset = queryset.filter(plugin_id=plugin_id)
        else:
            raise ValidationError({"plugin_id": "This field is required."})
        return queryset


@api_view(["GET", "POST", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def manage_plugin(request):
    if request.method == "GET":
        return get_plugin(request)
    if request.method == "POST":
        return create_plugin(request)
    if request.method == "PATCH":
        return update_plugin(request)
    if request.method == "DELETE":
        return delete_plugin(request)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


def get_plugin(request):
    # Access the JSON data sent in the request body
    account_id = UserProfile.objects.get(user=request.user).account.id
    plugin_id = request.data.get("plugin_id")

    if plugin_id:
        plugin = Plugin(plugin_id)
        return Response(plugin.to_json())

    account = AccountProvider(account_id)
    return account.plugins


def create_plugin(request):
    # Access the JSON data sent in the request body
    account_id = UserProfile.objects.get(user=request.user).account.id
    data = request.data
    data["account_id"] = account_id
    data["user_id"] = request.user.id

    # Process the data...
    plugin = Plugin.create(data=data)
    plugin = Plugin(plugin.id)

    return Response(plugin.to_json())


def update_plugin(request):
    account_id = UserProfile.objects.get(user=request.user).account.id
    data = request.data
    data["account_id"] = account_id
    data["user_id"] = request.user.id
    data["plugin_id"] = request.data.get("plugin_id")

    # Process the data...
    plugin = Plugin.update(data=data)
    plugin = Plugin(plugin.id)

    return Response(plugin.to_json())


def delete_plugin(request):
    account_id = UserProfile.objects.get(user=request.user).account.id
    data = request.data
    data["account_id"] = account_id
    data["user_id"] = request.user.id
    data["plugin_id"] = request.data.get("plugin_id")

    # Process the data...
    plugin = Plugin.delete(data=data)
    plugin = Plugin(plugin_id=plugin.id)

    return Response(plugin.to_json())
