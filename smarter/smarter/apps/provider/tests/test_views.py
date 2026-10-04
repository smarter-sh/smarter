"""
Test the Provider dashboard views: the React list page, its list, clone, delete and rename api,.

and the manifest detail page. See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.caching import (
    invalidate_all_cached_providers_for_user_profile,
)
from smarter.apps.provider.models import Provider
from smarter.apps.provider.urls import ProviderReverseNames
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin


class TestProviderViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the Provider dashboard views."""

    model = Provider
    reverse_names = ProviderReverseNames
    id_kwarg = "provider_id"
    invalidate_cache = staticmethod(invalidate_all_cached_providers_for_user_profile)
    resource_name_prefix = "test_provider_views"

    @classmethod
    def create_resource(cls, name: str) -> Provider:
        return Provider.objects.create(name=name, user_profile=cls.user_profile, base_url="https://api.example.com/v1/")

    def test_clone(self):
        super().test_clone()

    def test_delete(self):
        super().test_delete()

    def test_rename(self):
        super().test_rename()
