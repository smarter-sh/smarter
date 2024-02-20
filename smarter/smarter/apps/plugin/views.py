# -*- coding: utf-8 -*-
"""PluginMeta views."""

from http import HTTPStatus

from django.http import JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smarter.apps.account.models import UserProfile

from .plugin import Plugin, Plugins


@api_view(["GET", "PATCH", "DELETE"])
@permission_classes([IsAuthenticated])
def plugins_view(request, plugin_id):
    if request.method == "GET":
        return get_plugin(request, plugin_id)
    if request.method == "POST":
        return create_plugin(request)
    if request.method == "PATCH":
        return update_plugin(request)
    if request.method == "DELETE":
        return delete_plugin(request, plugin_id)
    return JsonResponse({"error": "Invalid HTTP method"}, status=405)


@api_view(["GET", "POST"])
@permission_classes([IsAuthenticated])
def plugin_clone_view(request, plugin_id: int, new_name: str):
    user_profile = UserProfile.objects.get(user=request.user)
    plugin = Plugin(plugin_id=plugin_id, user_profile=user_profile)
    new_id = plugin.clone(new_name)
    return redirect("/plugins/" + str(new_id) + "/")


@api_view(["GET"])
@permission_classes([IsAuthenticated])
def plugins_list_view(request):
    """Get a json list[dict] of all plugins for the current user."""
    plugins = Plugins(user=request.user)
    return Response(plugins.to_json(), status=HTTPStatus.OK)


# -----------------------------------------------------------------------
# handlers for plugins
# -----------------------------------------------------------------------
def get_plugin(request, plugin_id):
    """Get a plugin json representation by id."""
    user_profile = UserProfile.objects.get(user=request.user)
    plugin = Plugin(plugin_id=plugin_id, user_profile=user_profile)
    return Response(plugin.to_json(), status=HTTPStatus.OK)


def create_plugin(request):
    """Create a plugin from a json representation in the body of the request."""
    user_profile = UserProfile.objects.get(user=request.user)
    data = request.data
    data["user_profile"] = user_profile
    plugin = Plugin(data=data)
    return JsonResponse(plugin.to_json(), status=HTTPStatus.OK)


def update_plugin(request):
    """update a plugin from a json representation in the body of the request."""
    user_profile = UserProfile.objects.get(user=request.user)
    data = request.data
    data["user_profile"] = user_profile
    plugin = Plugin(data=data)
    return Response(plugin.to_json(), status=HTTPStatus.OK)


def delete_plugin(request, plugin_id):
    """delete a plugin by id."""
    user_profile = UserProfile.objects.get(user=request.user)
    plugin = Plugin(plugin_id=plugin_id, user_profile=user_profile)
    plugin.delete()
    return Response({"result": "success"}, status=HTTPStatus.OK)
