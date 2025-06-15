# pylint: disable=W0718
"""PluginMeta views."""

import json
from http import HTTPStatus
from typing import Optional
from urllib.parse import urljoin

import yaml
from django.conf import settings
from django.core.exceptions import ValidationError
from django.http import HttpResponseRedirect, JsonResponse
from django.shortcuts import redirect
from rest_framework import status
from rest_framework.parsers import FileUploadParser
from rest_framework.response import Response

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import get_cached_user_profile
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.apps.plugin.utils import add_example_plugins
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.user import User
from smarter.lib.drf.views.token_authentication_helpers import (
    SmarterAuthenticatedAPIView,
    SmarterAuthenticatedListAPIView,
)


class PluginView(SmarterAuthenticatedAPIView):
    """StaticPlugin view for smarter api."""

    def get(self, request, plugin_id):
        return get_plugin(request, plugin_id)

    def put(self, request):
        return create_plugin(request)

    def post(self, request):
        return create_plugin(request)

    def patch(self, request):
        return update_plugin(request)

    def delete(self, request, plugin_id):
        return delete_plugin(request, plugin_id)


class PluginCloneView(SmarterAuthenticatedAPIView):
    """StaticPlugin clone view for smarter api."""

    def post(self, request, plugin_id, new_name):
        user_profile = get_cached_user_profile(user=request.user)
        plugin = StaticPlugin(plugin_id=plugin_id, user_profile=user_profile)
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

    def post(self, request, user_id=None):
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
    """StaticPlugin view for smarter api."""

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

    def _create(self, request):
        data = self.parse_yaml_file(data=request.data)
        return create_plugin(request=request, data=data)

    def put(self, request):
        return self._create(request)

    def post(self, request):
        return self._create(request)


# -----------------------------------------------------------------------
# handlers for plugins
# -----------------------------------------------------------------------
def get_plugin(request, plugin_id):
    """Get a plugin json representation by id."""
    plugin: Optional[StaticPlugin] = None

    try:
        user_profile = get_cached_user_profile(user=request.user)
    except UserProfile.DoesNotExist:
        return JsonResponse({"error": "User not found"}, status=404)

    try:
        plugin = StaticPlugin(plugin_id=plugin_id, user_profile=user_profile)
    except PluginMeta.DoesNotExist:
        return JsonResponse({"error": "StaticPlugin not found"}, status=HTTPStatus.NOT_FOUND)
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
        plugin = StaticPlugin(data=data)
    except ValidationError as e:
        return JsonResponse({"error": e.message}, status=HTTPStatus.BAD_REQUEST)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    base_url = f"{settings.SMARTER_API_SCHEMA}://{request.get_host()}/"
    plugins_api_url = urljoin(base_url, "/api/v1/plugins/")

    return HttpResponseRedirect(plugins_api_url + str(plugin.id) + "/")


def update_plugin(request):
    """update a plugin from a json representation in the body of the request."""

    try:
        user_profile = get_cached_user_profile(user=request.user)
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
        StaticPlugin(data=data)
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
        plugin = StaticPlugin(plugin_id=plugin_id, user_profile=user_profile)
    except PluginMeta.DoesNotExist:
        return JsonResponse({"error": "StaticPlugin not found"}, status=HTTPStatus.NOT_FOUND)
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    try:
        plugin.delete()
    except Exception as e:
        return JsonResponse({"error": "Internal error", "exception": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    plugins_path = request.path_info.rsplit("/", 2)[0]
    return HttpResponseRedirect(plugins_path)
