"""
Test the LLMClient /api/v1/llm-clients/ endpoints, :mod:`smarter.apps.llmclient.api.v1.views.views`.

See :class:`smarter.lib.unittest.resource_api.ResourceApiTestMixin`.
"""

from http import HTTPStatus

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.llmclient.api.v1.urls import LLMClientApiV1ReverseViews as Names
from smarter.apps.llmclient.models import LLMClient
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
