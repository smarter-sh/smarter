"""
Test the LLMClient /api/v1/llm-clients/ endpoints, :mod:`smarter.apps.llmclient.api.v1.views.views`.

See :class:`smarter.lib.unittest.resource_api.ResourceApiTestMixin`.
"""

from http import HTTPStatus
from unittest.mock import patch

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.llmclient.api.v1.urls import LLMClientApiV1ReverseViews as Names
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientCustomDomain,
    LLMClientFunctions,
    LLMClientPlugin,
)
from smarter.apps.plugin.models import PluginMeta
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.unittest.resource_api import ResourceApiTestMixin


class TestLLMClientApi(ResourceApiTestMixin, ApiV1TestBase):
    """Test the LLMClient api."""

    model = LLMClient
    reverse_names = Names
    list_view = Names.llmclient_list_view
    view_by_hashed_id = Names.llmclient_view_by_hashed_id
    view_by_id = Names.llmclient_view_by_id
    default_api_by_hashed_id = Names.default_llmclient_api_view_by_hashed_id
    id_kwarg = "llmclient_id"
    resource_name_prefix = "test_llmclient_api"

    @classmethod
    def create_resource(cls, name: str) -> LLMClient:
        return LLMClient.objects.create(name=name, user_profile=cls.user_profile)

    def assert_sub_resource_lists(self):
        for name in (
            Names.llmclient_plugin_list_view_by_id,
            Names.llmclient_api_key_list_view_by_id,
            Names.llmclient_custom_domain_list_view_by_id,
            Names.llmclient_api_functions_by_id,
        ):
            with self.subTest(view=name):
                response = self.api_client.get(self.url(name, llmclient_id=self.resource.pk))
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])

    def assert_sub_resource_views(self):
        cases = {
            Names.llmclient_plugin_view_by_id: {"plugin_id": 999999999},
            Names.llmclient_api_key_view_by_id: {"apikey_id": 999999999},
            Names.llmclient_custom_domain_view_by_id: {"customdomain_id": 999999999},
            Names.llmclient_functions_view_by_id: {"function_id": 999999999},
        }
        for name, kwargs in cases.items():
            with self.subTest(view=name):
                response = self.api_client.get(self.url(name, llmclient_id=self.resource.pk, **kwargs))
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:300])

    def test_sub_resource_lists(self):
        """Test that the lists of the LLMClient's plugins, api keys, custom domains and functions are returned."""
        self.assert_sub_resource_lists()

    def test_sub_resource_views_not_found(self):
        """Test that an unknown plugin, api key, custom domain or function of the LLMClient is a 404."""
        self.assert_sub_resource_views()

    def test_custom_domain_attach_and_detach(self):
        """Test that a custom domain is attached to the LLMClient, refused for a second LLMClient, and detached."""
        domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile,
            aws_hosted_zone_id="Z0000000000TEST",
            domain_name=f"test-{self.hash_suffix}.example.com",
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=domain.pk).delete)
        url = self.url(
            Names.llmclient_custom_domain_view_by_id, llmclient_id=self.resource.pk, customdomain_id=domain.pk
        )

        response = self.api_client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:300])
        self.assertEqual(LLMClient.objects.get(pk=self.resource.pk).custom_domain_id, domain.pk)
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        self.assertEqual(response.json()["domainName"], domain.domain_name)

        other = self.create_resource(f"{self.resource_name_prefix}_{self.hash_suffix}_other")
        other_url = self.url(Names.llmclient_custom_domain_view_by_id, llmclient_id=other.pk, customdomain_id=domain.pk)
        self.assertEqual(self.api_client.post(other_url).status_code, HTTPStatus.CONFLICT)
        self.assertEqual(self.api_client.delete(other_url).status_code, HTTPStatus.NOT_FOUND)

        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:300])
        self.assertIsNone(LLMClient.objects.get(pk=self.resource.pk).custom_domain_id)
        # detaching keeps the domain, whose deletion would cascade to the LLMClient.
        self.assertTrue(LLMClientCustomDomain.objects.filter(pk=domain.pk).exists())

    def test_attaching_a_verified_domain_deploys_the_llmclient_on_it(self):
        """A deployed llmclient is deployed on its custom host when a verified custom domain is attached."""
        domain = LLMClientCustomDomain.objects.create(
            user_profile=self.user_profile,
            aws_hosted_zone_id="Z0000000000TEST",
            domain_name=f"test-verified-{self.hash_suffix}.example.com",
        )
        self.addCleanup(LLMClientCustomDomain.objects.filter(pk=domain.pk).delete)
        domain.set_verification_status(LLMClientCustomDomain.VerificationStatusChoices.VERIFIED)
        llmclient = self.create_resource(f"{self.resource_name_prefix}_{self.hash_suffix}_custom")
        # update(), rather than save(), which would queue a real deployment.
        LLMClient.objects.filter(pk=llmclient.pk).update(deployed=True)
        url = self.url(Names.llmclient_custom_domain_view_by_id, llmclient_id=llmclient.pk, customdomain_id=domain.pk)

        with patch("smarter.apps.llmclient.api.v1.views.views.deploy_custom_api") as deploy_custom_api:
            response = self.api_client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:300])
        deploy_custom_api.delay.assert_called_once_with(llmclient_id=llmclient.pk)

    def test_plugin_view(self):
        """Test that an LLMClient's plugin is returned, refuses invalid data, and is removed."""
        plugin_meta = PluginMeta.objects.create(
            name=f"test_llmclient_api_plugin_{self.hash_suffix}", user_profile=self.user_profile, plugin_class="static"
        )
        self.addCleanup(PluginMeta.objects.filter(pk=plugin_meta.pk).delete)
        llmclient_plugin = LLMClientPlugin.objects.create(llmclient=self.resource, plugin_meta=plugin_meta)
        url = self.url(Names.llmclient_plugin_view_by_id, llmclient_id=self.resource.pk, plugin_id=llmclient_plugin.pk)

        response = self.api_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])

        response = self.api_client.patch(url, data="not json", content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.content[:300])
        response = self.api_client.patch(url, data={"kind": "NotAPlugin"}, format="json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.content[:300])

        list_url = self.url(Names.llmclient_plugin_list_view_by_id, llmclient_id=self.resource.pk)
        response = self.api_client.post(list_url, data={"kind": "NotAPlugin"}, format="json")
        self.assertIn(response.status_code, (HTTPStatus.BAD_REQUEST, HTTPStatus.METHOD_NOT_ALLOWED))

        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:300])
        self.assertFalse(LLMClientPlugin.objects.filter(pk=llmclient_plugin.pk).exists())

    def test_api_key_view(self):
        """Test that an LLMClient's api key is returned and removed."""
        token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile,
            name=f"test_llmclient_api_key_{self.hash_suffix}",
            user=self.admin_user,
            description="test llmclient api key",
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=token.pk).delete)
        # the post route takes an int apikey_id, which can't address a token, whose key is a digest.
        llmclient_api_key = LLMClientAPIKey.objects.create(llmclient=self.resource, api_key=token)

        url = self.url(
            Names.llmclient_api_key_view_by_id, llmclient_id=self.resource.pk, apikey_id=llmclient_api_key.pk
        )
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])

        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:300])
        self.assertFalse(LLMClientAPIKey.objects.filter(pk=llmclient_api_key.pk).exists())

    def test_function_view(self):
        """Test that an LLMClient's function is returned and removed."""
        function = LLMClientFunctions.objects.create(llmclient=self.resource, name="calculator")
        url = self.url(Names.llmclient_functions_view_by_id, llmclient_id=self.resource.pk, function_id=function.pk)
        response = self.api_client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        response = self.api_client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:300])
        self.assertFalse(LLMClientFunctions.objects.filter(pk=function.pk).exists())

    def test_list(self):
        super().test_list()

    def test_list_with_api_key(self):
        super().test_list_with_api_key()

    def test_get(self):
        super().test_get()

    def test_get_not_found(self):
        super().test_get_not_found()

    def test_post_invalid(self):
        super().test_post_invalid()

    def test_patch(self):
        super().test_patch()

    def test_delete(self):
        super().test_delete()

    def test_default_api_get_and_options(self):
        super().test_default_api_get_and_options()
