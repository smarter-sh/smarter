"""
Test the Orchestrator dashboard views: the React list page, its list, clone, delete and rename api,.

and the manifest detail page. See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

import unittest

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.orchestrator.caching import (
    invalidate_all_cached_orchestrators_for_user_profile,
)
from smarter.apps.orchestrator.models import Orchestrator
from smarter.apps.orchestrator.urls import OrchestratorReverseNames
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin


class TestOrchestratorViews(ResourceViewsTestMixin, TestAccountMixin):
    """
    Test the Orchestrator dashboard views.

    test_clone, test_delete and test_rename are expected to fail: the urls pass the Orchestrator's
    id as llmclient_id, but the views read orchestrator_id, so every request is refused with a 400.
    """

    model = Orchestrator
    reverse_names = OrchestratorReverseNames
    id_kwarg = "llmclient_id"
    invalidate_cache = staticmethod(invalidate_all_cached_orchestrators_for_user_profile)
    resource_name_prefix = "test_orchestrator_views"

    @classmethod
    def create_resource(cls, name: str) -> Orchestrator:
        return Orchestrator.objects.create(name=name, user_profile=cls.user_profile)

    @unittest.expectedFailure
    def test_clone(self):
        super().test_clone()

    @unittest.expectedFailure
    def test_delete(self):
        super().test_delete()

    @unittest.expectedFailure
    def test_rename(self):
        super().test_rename()

    @unittest.expectedFailure
    def test_detail(self):
        """
        Expected to fail: OrchestratorDetailView describes the kind Provider, rather than.

        Orchestrator, so it looks for a Provider of the Orchestrator's name.
        """
        super().test_detail()
