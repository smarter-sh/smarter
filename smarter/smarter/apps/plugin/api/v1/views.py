# pylint: disable=W0718
"""PluginMeta views."""

import json
from http import HTTPStatus
from typing import Optional
from urllib.parse import urljoin

import yaml
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from smarter.apps.account.models import UserClass as User
from smarter.apps.account.models import UserProfile, get_resolved_user
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.plugin.models import PluginDataValueError, PluginMeta
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.apps.plugin.utils import add_example_plugins
from smarter.common.exceptions import SmarterValueError
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)


class PluginView(SmarterAuthenticatedAPIView):
    """Plugin view for smarter api."""

    def get(self, request: WSGIRequest, plugin_id):
        return get_plugin(request, plugin_id)

    def put(self, request: WSGIRequest):
        return create_plugin(request)

    def post(self, request: WSGIRequest):
        return create_plugin(request)

    def patch(self, request: WSGIRequest):
        return update_plugin(request)

    def delete(self, request: WSGIRequest, plugin_id):
        return delete_plugin(request, plugin_id)


class PluginCloneView(SmarterAuthenticatedAPIView):
    """Plugin clone view for smarter api."""

    def post(self, request: WSGIRequest, plugin_id, new_name):
        user = get_resolved_user(request.user)
        if not user:
            return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)
        user_profile = get_cached_user_profile(user=user)
        plugin_controller = PluginController(
            user_profile=user_profile,
            account=user_profile.account,  # type: ignore[arg-type]
            user=user_profile.user,  # type: ignore[arg-type]
            plugin_meta=PluginMeta.objects.get(id=plugin_id),
        )
        if not plugin_controller or not plugin_controller.plugin:
            return JsonResponse(
                {
                    "error": f"PluginController could not be created for plugin_id: {plugin_id}, user_profile: {user_profile}"
                },
                status=HTTPStatus.BAD_REQUEST,
            )
        plugin = plugin_controller.plugin
        new_id = plugin.clone(new_name)
        return redirect("/plugins/" + str(new_id) + "/")


class PluginListView(SmarterAuthenticatedListAPIView):
    """Plugins list view for smarter api."""

    serializer_class = PluginMetaSerializer

    def get_queryset(self):
        plugins = PluginMeta.objects.filter(author__user=self.request.user)
        return plugins


class AddPluginExamplesView(SmarterAuthenticatedAPIView):
    """Add example plugins to a user profile."""

    def post(self, request: WSGIRequest, user_id=None):
        try:
            user = User.objects.get(id=user_id) if user_id else request.user
            user_profile = get_cached_user_profile(user=user)  # type: ignore
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            add_example_plugins(user_profile=user_profile)
        except Exception as e:
            return Response(
                {"error": "Internal error", "exception": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

        return HttpResponseRedirect("/v1/plugins/")


class PluginUploadView(SmarterAuthenticatedAPIView):
    """Plugin view for smarter api."""

    parser_class = (FileUploadParser,)

    @staticmethod
    def parse_yaml_file(data):

        if type(data) in [dict, list]:
            return data

        if isinstance(data, str):
            data = data.encode("utf-8")

        try:
            return yaml.safe_load(data)
        except yaml.YAMLError:
            pass

        try:
            return json.loads(data)
        except json.JSONDecodeError:
            pass

        raise SmarterValueError("Invalid data format: expected JSON or YAML.")

    def _create(self, request: WSGIRequest):
        data = self.parse_yaml_file(data=request.body.decode("utf-8"))
        return create_plugin(request=request, data=data)

    def put(self, request: WSGIRequest):
        return self._create(request)

    def post(self, request: WSGIRequest):
        return self._create(request)


# -----------------------------------------------------------------------
# handlers for plugins
# -----------------------------------------------------------------------
def get_plugin(request, plugin_id):
    """Get a plugin json representation by id."""
    plugin: Optional[PluginBase] = None

    try:
        user_profile = get_cached_user_profile(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    try:
        plugin_controller = PluginController(
            user_profile=user_profile,
            account=user_profile.account,  # type: ignore[arg-type]
            user=user_profile.user,  # type: ignore[arg-type]
            plugin_meta=PluginMeta.objects.get(id=plugin_id),
        )
        if not plugin_controller or not plugin_controller.plugin:
            raise PluginDataValueError(
                f"PluginController could not be created for plugin_id: {plugin_id}, user_profile: {user_profile}"
            )
        plugin = plugin_controller.plugin
    except PluginMeta.DoesNotExist:
        return JsonResponse({"error": "Plugin not found"}, status=HTTPStatus.NOT_FOUND)
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    if plugin.ready:
        return JsonResponse(plugin.to_json(), status=HTTPStatus.OK)
    return JsonResponse({"error": "Internal plugin error."}, status=HTTPStatus.INTERNAL_SERVER_ERROR)


def create_plugin(request, data: Optional[dict] = None):
    """Create a plugin from a json representation in the body of the request."""
    try:
        user_profile = get_cached_user_profile(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    if not data:
        try:
            data = request.data
            if not isinstance(data, dict):
                return JsonResponse(
                    {"error": f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"},
                    status=HTTPStatus.BAD_REQUEST,
                )
        except Exception as e:
            return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    if "user_profile" not in data:
        data["user_profile"] = user_profile

    try:
        plugin_controller = PluginController(
            user_profile=user_profile,
            account=user_profile.account,  # type: ignore[arg-type]
            user=user_profile.user,  # type: ignore[arg-type]
            manifest=data,  # type: ignore[arg-type]
        )
        if not plugin_controller or not plugin_controller.plugin:
            raise PluginDataValueError(
                f"PluginController could not be created for data: {data}, user_profile: {user_profile}"
            )
        plugin = plugin_controller.plugin
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    base_url = f"{settings.SMARTER_API_SCHEMA}://{request.get_host()}/"
    plugins_api_url = urljoin(base_url, "/api/v1/plugins/")

    return HttpResponseRedirect(plugins_api_url + str(plugin.id) + "/")


def update_plugin(request: WSGIRequest):
    """update a plugin from a json representation in the body of the request."""
    user = get_resolved_user(request.user)
    data: str

    if not user:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)
    try:
        user_profile = get_cached_user_profile(user=user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        data = request.body.decode("utf-8")
        if not isinstance(data, dict):
            return JsonResponse(
                {"error": f"Invalid request data. Expected a JSON dict in request body but received {type(data)}"},
                status=HTTPStatus.BAD_REQUEST,
            )

        data["user_profile"] = user_profile
    except Exception as e:
        return JsonResponse({"error": "Invalid request data", "exception": str(e)}, status=HTTPStatus.BAD_REQUEST)

    try:
        data = json.loads(data)
    except json.JSONDecodeError:
        return JsonResponse({"error": "Invalid JSON format"}, status=HTTPStatus.BAD_REQUEST)

    if not user_profile:
        return JsonResponse({"error": "User profile not found"}, status=HTTPStatus.UNAUTHORIZED)
    try:
        plugin_controller = PluginController(
            user_profile=user_profile,
            account=user_profile.account,
            user=user_profile.user,
            manifest=SAMPluginCommon(**data),  # type: ignore[arg-type]
        )
        if not plugin_controller or not plugin_controller.plugin:
            raise PluginDataValueError(
                f"PluginController could not be created for data: {data}, user_profile: {user_profile}"
            )
        plugin = plugin_controller.plugin
        if not plugin:
            return JsonResponse({"error": "Plugin not found"}, status=HTTPStatus.NOT_FOUND)
        if not data:
            return JsonResponse({"error": "No data provided for update"}, status=HTTPStatus.BAD_REQUEST)
        plugin.update()
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    return HttpResponseRedirect(request.path_info)


def delete_plugin(request, plugin_id):
    """delete a plugin by id."""
    try:
        user_profile = get_cached_user_profile(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=HTTPStatus.UNAUTHORIZED)

    try:
        plugin_controller = PluginController(
            user_profile=user_profile,
            account=user_profile.account,  # type: ignore[arg-type]
            user=user_profile.user,  # type: ignore[arg-type]
            plugin_meta=PluginMeta.objects.get(id=plugin_id),
        )
        if not plugin_controller or not plugin_controller.plugin:
            raise PluginDataValueError(
                f"PluginController could not be created for plugin_id: {plugin_id}, user_profile: {user_profile}"
            )
        plugin = plugin_controller.plugin
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
