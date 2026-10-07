"""Test the error responses of the LLMClient /api/v1/llm-clients/ endpoints, :mod:`smarter.apps.llmclient.api.v1.views.views`."""

from http import HTTPStatus
from unittest.mock import patch

from django.core.exceptions import ValidationError
from django.urls import reverse
from rest_framework.test import APIClient, APIRequestFactory, force_authenticate

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.llmclient.api.v1.urls import LLMClientApiV1ReverseViews as Names
from smarter.apps.llmclient.api.v1.views.views import (
    LLMClientAPIKeyView,
    LLMClientDeployView,
    LLMClientFunctionsView,
    LLMClientPluginView,
    LLMClientView,
)
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientFunctions,
    LLMClientPlugin,
)
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.drf.models import SmarterAuthToken


class TestLLMClientApiErrors(ApiV1TestBase):
    """Test that invalid requests and failing saves or deletes return error responses."""

    def setUp(self):
        super().setUp()
        self.api_client = APIClient()
        self.api_client.force_login(self.admin_user)
        self.addCleanup(self.api_client.logout)
        self.llmclient = LLMClient.objects.create(
            name=f"test_llmclient_api_errors_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)

    def url(self, name: str, **kwargs) -> str:
        return reverse(f"{Names.namespace}:{name}", kwargs=kwargs or None)

    def assertStatus(self, response, status: int):
        self.assertEqual(response.status_code, status, response.content[:300])

    def test_patch_needs_a_dict(self):
        """Patching an LLMClient with a body that isn't a dict is a bad request."""
        url = self.url(Names.llmclient_view_by_id, llmclient_id=self.llmclient.pk)
        self.assertStatus(self.api_client.patch(url, data=[1, 2], format="json"), HTTPStatus.BAD_REQUEST)

    def test_patch_save_failures(self):
        """A failed validation is a bad request, and any other save failure is an internal error."""
        url = self.url(Names.llmclient_view_by_id, llmclient_id=self.llmclient.pk)
        with patch.object(LLMClient, "save", side_effect=ValidationError("invalid")):
            self.assertStatus(
                self.api_client.patch(url, data={"description": "x"}, format="json"), HTTPStatus.BAD_REQUEST
            )
        with patch.object(LLMClient, "save", side_effect=RuntimeError("database down")):
            self.assertStatus(
                self.api_client.patch(url, data={"description": "x"}, format="json"), HTTPStatus.INTERNAL_SERVER_ERROR
            )

    def test_delete_failure(self):
        """A failed delete is an internal error."""
        url = self.url(Names.llmclient_view_by_id, llmclient_id=self.llmclient.pk)
        with patch.object(LLMClient, "delete", side_effect=RuntimeError("database down")):
            self.assertStatus(self.api_client.delete(url), HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_custom_domain_get(self):
        """An LLMClient's custom domain is returned."""
        domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile,
            aws_hosted_zone_id="Z0000000000TEST",
            domain_name=f"errors-{self.hash_suffix}.example.com",
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=domain.pk).delete)
        LLMClient.objects.filter(pk=self.llmclient.pk).update(custom_domain=domain)
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).update, custom_domain=None)
        url = self.url(
            Names.llmclient_custom_domain_view_by_id, llmclient_id=self.llmclient.pk, customdomain_id=domain.pk
        )
        response = self.api_client.get(url)
        self.assertStatus(response, HTTPStatus.OK)

    def test_plugin_patch_and_delete_failure(self):
        """A plugin is updated by patch, and a failed delete is an internal error."""
        plugin_meta = PluginMeta.objects.create(
            name=f"test_llmclient_api_errors_{self.hash_suffix}", user_profile=self.user_profile, plugin_class="static"
        )
        self.addCleanup(PluginMeta.objects.filter(pk=plugin_meta.pk).delete)
        llmclient_plugin = LLMClientPlugin.objects.create(llmclient=self.llmclient, plugin_meta=plugin_meta)
        url = self.url(Names.llmclient_plugin_view_by_id, llmclient_id=self.llmclient.pk, plugin_id=llmclient_plugin.pk)

        with patch.object(LLMClientPlugin, "load", return_value=llmclient_plugin):
            self.assertStatus(self.api_client.patch(url, data={"name": "x"}, format="json"), HTTPStatus.FOUND)
        with patch.object(LLMClientPlugin, "delete", side_effect=RuntimeError("database down")):
            self.assertStatus(self.api_client.delete(url), HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_api_key_delete_failure(self):
        """A failed api key delete is an internal error."""
        token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile,
            name=f"test_llmclient_api_errors_{self.hash_suffix}",
            user=self.admin_user,
            description="test llmclient api key",
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=token.pk).delete)
        llmclient_api_key = LLMClientAPIKey.objects.create(llmclient=self.llmclient, api_key=token)
        url = self.url(
            Names.llmclient_api_key_view_by_id, llmclient_id=self.llmclient.pk, apikey_id=llmclient_api_key.pk
        )
        with patch.object(LLMClientAPIKey, "delete", side_effect=RuntimeError("database down")):
            self.assertStatus(self.api_client.delete(url), HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_function_delete_failure(self):
        """A failed function delete is an internal error."""
        function = LLMClientFunctions.objects.create(llmclient=self.llmclient, name="calculator")
        self.addCleanup(LLMClientFunctions.objects.filter(pk=function.pk).delete)
        url = self.url(Names.llmclient_functions_view_by_id, llmclient_id=self.llmclient.pk, function_id=function.pk)
        with patch.object(LLMClientFunctions, "delete", side_effect=RuntimeError("database down")):
            self.assertStatus(self.api_client.delete(url), HTTPStatus.INTERNAL_SERVER_ERROR)

    def call_view(self, view_class, method: str, data=None, **kwargs):
        """Call a view directly, for the handlers that no url routes to with these arguments."""
        request = getattr(APIRequestFactory(), method)("/api/v1/llm-clients/", data=data, format="json")
        force_authenticate(request, user=self.admin_user)
        request.user = self.admin_user
        response = view_class.as_view()(request, **kwargs)
        if hasattr(response, "render"):
            response.render()
        return response

    def test_llmclient_view_without_an_llmclient(self):
        """Getting or patching without an LLMClient is not found."""
        self.assertStatus(self.call_view(LLMClientView, "get"), HTTPStatus.NOT_FOUND)
        self.assertStatus(self.call_view(LLMClientView, "patch", data={"description": "x"}), HTTPStatus.NOT_FOUND)

    def test_llmclient_view_queryset(self):
        view = LLMClientView()
        view.llmclient = self.llmclient
        self.assertEqual(list(view.get_queryset()), [self.llmclient])

    def test_deploy(self):
        """Deploying sets deployed, and a failed save is a bad request."""
        with patch.object(LLMClient, "save") as save:
            self.assertStatus(
                self.call_view(LLMClientDeployView, "post", llmclient_id=self.llmclient.pk), HTTPStatus.OK
            )
        save.assert_called_once()
        with patch.object(LLMClient, "save", side_effect=RuntimeError("database down")):
            self.assertStatus(
                self.call_view(LLMClientDeployView, "post", llmclient_id=self.llmclient.pk), HTTPStatus.BAD_REQUEST
            )

    def test_plugin_post(self):
        """Adding a plugin redirects to it, and a plugin that fails to load is a bad request."""
        with patch.object(LLMClientPlugin, "load", return_value=LLMClientPlugin(id=123)):
            response = self.call_view(LLMClientPluginView, "post", data={"name": "x"}, llmclient_id=self.llmclient.pk)
        self.assertStatus(response, HTTPStatus.FOUND)
        self.assertTrue(response["Location"].endswith("123/"))
        with patch.object(LLMClientPlugin, "load", side_effect=RuntimeError("bad plugin")):
            response = self.call_view(LLMClientPluginView, "post", data={"name": "x"}, llmclient_id=self.llmclient.pk)
        self.assertStatus(response, HTTPStatus.BAD_REQUEST)

    def test_api_key_post(self):
        """Adding an api key redirects to it, and a failed create is a bad request."""
        token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile,
            name=f"test_llmclient_api_errors_post_{self.hash_suffix}",
            user=self.admin_user,
            description="test llmclient api key",
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=token.pk).delete)
        self.addCleanup(LLMClientAPIKey.objects.filter(llmclient=self.llmclient).delete)
        kwargs = {"llmclient_id": self.llmclient.pk, "apikey_id": token.pk}
        self.assertStatus(self.call_view(LLMClientAPIKeyView, "post", **kwargs), HTTPStatus.FOUND)
        self.assertTrue(LLMClientAPIKey.objects.filter(llmclient=self.llmclient, api_key=token).exists())
        with patch.object(LLMClientAPIKey.objects, "create", side_effect=RuntimeError("database down")):
            self.assertStatus(self.call_view(LLMClientAPIKeyView, "post", **kwargs), HTTPStatus.BAD_REQUEST)

    def test_function_post_is_not_implemented(self):
        with self.assertRaises(NotImplementedError):
            self.call_view(LLMClientFunctionsView, "post", llmclient_id=self.llmclient.pk)
