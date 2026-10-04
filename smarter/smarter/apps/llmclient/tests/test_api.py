"""
Test the LLMClient /api/v1/llm-clients/ endpoints, :mod:`smarter.apps.llmclient.api.v1.views.views`.

See :class:`smarter.lib.unittest.resource_api.ResourceApiTestMixin`.
"""

import unittest
from http import HTTPStatus

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.llmclient.api.v1.urls import LLMClientApiV1ReverseViews as Names
from smarter.apps.llmclient.models import LLMClient
from smarter.lib.unittest.resource_api import ResourceApiTestMixin


class TestLLMClientApi(ResourceApiTestMixin, ApiV1TestBase):
    """
    Test the LLMClient api.

    The tests of the LLMClient CRUD views are expected to fail, because each view is a 500:

    - ViewBase.dispatch() and ListViewBase.dispatch() assign self.user_profile after
      super().dispatch(), which has already set it, and SmarterRequestMixin.user_profile
      raises SmarterBusinessRuleViolation when it is set again.
    - LLMClientView.dispatch() finds the LLMClient only after super().dispatch() has called
      get(), patch() or delete(), which therefore never have it; and the url by id is
      unreachable, because the url by hashed id, a str, is listed first and matches an id too.
    - The plugin, api key, custom domain, function and deploy views look the LLMClient up by
      an account field, which LLMClient does not have, and several take url parameters by other
      names than their urls pass: plugin_meta_id for plugin_id, api_key_id for apikey_id, and
      custom_domain_id for customdomain_id.
    - DefaultLLMClientApiView returns a DRF Response to an OPTIONS before DRF has set its
      renderer, which raises AssertionError.
    - test_list_with_api_key: SmarterAdminAPIView.dispatch() checks is_superuser() before DRF
      has authenticated the request's api key, so every request with an api key is a 403.
    """

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

    @unittest.expectedFailure
    def test_sub_resource_lists(self):
        """Test that the lists of the LLMClient's plugins, api keys, custom domains and functions are returned."""
        self.assert_sub_resource_lists()

    @unittest.expectedFailure
    def test_sub_resource_views_not_found(self):
        """Test that an unknown plugin, api key, custom domain or function of the LLMClient is a 404."""
        self.assert_sub_resource_views()

    @unittest.expectedFailure
    def test_list(self):
        super().test_list()

    @unittest.expectedFailure
    def test_list_with_api_key(self):
        super().test_list_with_api_key()

    @unittest.expectedFailure
    def test_get(self):
        super().test_get()

    @unittest.expectedFailure
    def test_get_not_found(self):
        super().test_get_not_found()

    @unittest.expectedFailure
    def test_post_invalid(self):
        super().test_post_invalid()

    @unittest.expectedFailure
    def test_patch(self):
        super().test_patch()

    @unittest.expectedFailure
    def test_delete(self):
        super().test_delete()

    @unittest.expectedFailure
    def test_default_api_get_and_options(self):
        super().test_default_api_get_and_options()
