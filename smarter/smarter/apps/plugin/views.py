# -*- coding: utf-8 -*-
# pylint: disable=W0718
"""PluginMeta views."""

from http import HTTPStatus

from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from smarter.apps.account.models import UserProfile

from .models import PluginMeta
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
    plugin: Plugin = None

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    try:
        plugin = Plugin(plugin_id=plugin_id, user_profile=user_profile)
    except PluginMeta.DoesNotExist:
        return JsonResponse({"error": "Plugin not found"}, status=HTTPStatus.NOT_FOUND)
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if plugin.ready:
        return JsonResponse(plugin.to_json(), status=HTTPStatus.OK)
    return JsonResponse({"error": "Internal plugin error."}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def create_plugin(request):
    """Create a plugin from a json representation in the body of the request."""
    data: dict = None

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        data = request.data
        if not isinstance(data, dict):
            return JsonResponse(
                {"error": f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"},
                status=HTTPStatus.BAD_REQUEST,
            )
        data["user_profile"] = user_profile
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    try:
        plugin = Plugin(data=data)
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return HttpResponseRedirect(request.path_info + str(plugin.id) + "/")


def update_plugin(request):
    """update a plugin from a json representation in the body of the request."""

    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        data = request.data
        if not isinstance(data, dict):
            return JsonResponse(
                {"error": f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"},
                status=HTTPStatus.BAD_REQUEST,
            )

        data["user_profile"] = user_profile
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    try:
        Plugin(data=data)
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return HttpResponseRedirect(request.path_info)


def delete_plugin(request, plugin_id):
    """delete a plugin by id."""
    try:
        user_profile = UserProfile.objects.get(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        plugin = Plugin(plugin_id=plugin_id, user_profile=user_profile)
    except PluginMeta.DoesNotExist:
        return JsonResponse({"error": "Plugin not found"}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        plugin.delete()
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    plugins_path = request.path_info.rsplit("/", 2)[0]
    return HttpResponseRedirect(plugins_path)
