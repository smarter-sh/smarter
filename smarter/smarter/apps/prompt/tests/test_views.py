"""
Test the Prompt dashboard views: the React list of LLMClients, its list, clone, delete and rename api, the LLMClient manifest page, and the sandbox, prompt workbench and config pages.

See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from http import HTTPStatus
from urllib.parse import urlparse

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.caching import (
    invalidate_all_cached_llmclients_for_user_profile,
)
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.common.conf import smarter_settings
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin

PLATFORM_HOST = urlparse(smarter_settings.environment_platform_url).netloc


class TestPromptViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the Prompt dashboard views, whose resource is an LLMClient."""

    model = LLMClient
    reverse_names = PromptReverseNames
    id_kwarg = "llmclient_id"
    invalidate_cache = staticmethod(invalidate_all_cached_llmclients_for_user_profile)
    resource_name_prefix = "test_prompt_views"
    detail_view_name = "manifest_by_hashed_id"

    @classmethod
    def create_resource(cls, name: str) -> LLMClient:
        return LLMClient.objects.create(name=name, user_profile=cls.user_profile)

    def test_detail(self):
        super().test_detail()

    def test_config_other_account(self):
        """Test that another account's admin cannot read the LLMClient's configuration."""
        other_admin_user, _, _ = admin_user_factory()
        # admin_user_factory() users are superusers, who may read every account's resources.
        other_admin_user.is_superuser = False
        other_admin_user.save()
        self.client.force_login(other_admin_user)
        response = self.client.post(self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertIn(response.status_code, (HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND), response.content[:300])

    def test_sandbox(self):
        """Test that the sandbox url, which only provides the base url of the workbench pages, is a 404."""
        response = self.client.get(self.url("sandbox_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_config(self):
        """Test that the config api returns the LLMClient's configuration to a POST, and refuses a GET."""
        url = self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id)
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertEqual(self.client.get(url).status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_workbench(self):
        """Test that the prompt workbench page renders, for a request to the platform's host."""
        response = self.client.get(
            self.url("chat_by_hashed_id", hashed_id=self.resource.hashed_id), HTTP_HOST=PLATFORM_HOST
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])

    def test_workbench_and_config_not_found(self):
        """Test that the workbench page and config api are a 404 for an unknown LLMClient."""
        unknown = LLMClient(id=999999999)
        response = self.client.get(self.url("chat_by_hashed_id", hashed_id=unknown.hashed_id), HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.client.post(self.url("config_by_hashed_id", hashed_id=unknown.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
