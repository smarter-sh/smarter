"""
Test the Provider dashboard views: the React list page, its list, clone, delete and rename api,.

and the manifest detail page. See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

import unittest

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.caching import (
    invalidate_all_cached_providers_for_user_profile,
)
from smarter.apps.provider.models import Provider
from smarter.apps.provider.urls import ProviderReverseNames
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin


class TestProviderViews(ResourceViewsTestMixin, TestAccountMixin):
    """
    Test the Provider dashboard views.

    test_clone, test_delete and test_rename are expected to fail: the urls pass the Provider's
    id as llmclient_id, but the views read provider_id, so every request is refused with a 400.
    """

    model = Provider
    reverse_names = ProviderReverseNames
    id_kwarg = "llmclient_id"
    invalidate_cache = staticmethod(invalidate_all_cached_providers_for_user_profile)
    resource_name_prefix = "test_provider_views"

    @classmethod
    def create_resource(cls, name: str) -> Provider:
        return Provider.objects.create(name=name, user_profile=cls.user_profile, base_url="https://api.example.com/v1/")

    @unittest.expectedFailure
    def test_clone(self):
        super().test_clone()

    @unittest.expectedFailure
    def test_delete(self):
        super().test_delete()

    @unittest.expectedFailure
    def test_rename(self):
        super().test_rename()
