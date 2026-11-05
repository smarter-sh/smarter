"""
Test the Provider dashboard views: the React list page, its list, clone, delete and rename api, and the manifest detail page.

See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from http import HTTPStatus
from unittest.mock import patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.api.web.urls import ProviderApiWebReverseNames
from smarter.apps.provider.caching import (
    invalidate_all_cached_providers_for_user_profile,
)
from smarter.apps.provider.manifest.brokers.provider import (
    SAMProviderBroker,
    SAMProviderBrokerError,
)
from smarter.apps.provider.models import Provider
from smarter.apps.provider.urls import ProviderReverseNames
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin


class TestProviderViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the Provider dashboard views."""

    model = Provider
    reverse_names = ProviderReverseNames
    web_reverse_names = ProviderApiWebReverseNames
    id_kwarg = "provider_id"
    invalidate_cache = staticmethod(invalidate_all_cached_providers_for_user_profile)
    resource_name_prefix = "test_provider_views"

    @classmethod
    def create_resource(cls, name: str) -> Provider:
        return Provider.objects.create(name=name, user_profile=cls.user_profile, base_url="https://api.example.com/v1/")

    def test_web_api_paths(self):
        """Test that the list page's endpoints are in the web console's api."""
        self.assertEqual(self.web_url("listview_all"), "/api/web/provider/listview/")
        self.assertEqual(self.web_url("listview", ownership_filter="owned"), "/api/web/provider/listview/owned/")
        self.assertEqual(self.web_id_url("clone", 1, new_name="x"), "/api/web/provider/clone/1/x/")
        self.assertEqual(self.web_id_url("rename", 1, new_name="x"), "/api/web/provider/rename/1/x/")
        self.assertEqual(self.web_id_url("delete", 1), "/api/web/provider/delete/1/")

    def test_clone(self):
        super().test_clone()

    def test_delete(self):
        super().test_delete()

    def test_rename(self):
        super().test_rename()

    def test_detail_reports_a_describe_error(self):
        """A describe error is shown with the api's status and description, rather than as a 500."""
        with patch.object(SAMProviderBroker, "describe", side_effect=SAMProviderBrokerError("describe is broken")):
            response = self.client.get(self.url(self.detail_view_name, hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.content[:500])
