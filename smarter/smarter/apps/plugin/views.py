# -*- coding: utf-8 -*-
"""PluginMeta views."""

from django.http import JsonResponse
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .plugin import Plugin, Plugins


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def plugin_view(request, plugin_id):
    if request.method == "GET":
        return get_plugin(request, plugin_id)
    if request.method == "PATCH":
        return update_plugin(request)
    if request.method == "DELETE":
        return delete_plugin(request, plugin_id)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@api_view(["POST"])
@permission_classes([IsAuthenticated])
def plugin_create_view(request):
    """Create a plugin from a json representation in the body of the request."""
    data = request.data
    plugin = Plugin(user_id=request.user.id, data=data)
    return JsonResponse(plugin.to_json(), status=405)


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def plugins_view(request):
    """Get a json list[dict] of all plugins for the current user."""
    plugins = Plugins(user_id=request.user.id)
    return Response(plugins.to_json())


# -----------------------------------------------------------------------
# handlers for plugins
# -----------------------------------------------------------------------
def get_plugin(request, plugin_id):
    """Get a plugin json representation by id."""
    plugin = Plugin(plugin_id=plugin_id, user_id=request.user.id)
    return Response(plugin.to_json())


def update_plugin(request):
    """update a plugin from a json representation in the body of the request."""
    data = request.data
    data["user"] = request.user.id
    plugin = Plugin(data=data)
    return Response(plugin.to_json())


def delete_plugin(request, plugin_id):
    """delete a plugin by id."""
    plugin = Plugin(user_id=request.user.id, plugin_id=plugin_id)
    plugin.delete()
    return Response({"result": "success"})
