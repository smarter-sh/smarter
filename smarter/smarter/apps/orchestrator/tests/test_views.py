"""
Test the Orchestrator dashboard views: the React list page, its list, clone, delete and rename api, and the manifest detail page.

See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.orchestrator.caching import (
    invalidate_all_cached_orchestrators_for_user_profile,
)
from smarter.apps.orchestrator.models import Orchestrator, OrchestratorHarness
from smarter.apps.orchestrator.urls import OrchestratorReverseNames
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin


class TestOrchestratorViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the Orchestrator dashboard views."""

    model = Orchestrator
    reverse_names = OrchestratorReverseNames
    id_kwarg = "orchestrator_id"
    invalidate_cache = staticmethod(invalidate_all_cached_orchestrators_for_user_profile)
    resource_name_prefix = "test_orchestrator_views"

    @classmethod
    def create_resource(cls, name: str) -> Orchestrator:
        # a manifest requires at least one harness, so the detail page needs one to describe.
        orchestrator = Orchestrator.objects.create(name=name, user_profile=cls.user_profile)
        llmclient = LLMClient.objects.create(name=name, user_profile=cls.user_profile)
        OrchestratorHarness.objects.create(orchestrator=orchestrator, llmclient=llmclient)
        return orchestrator

    @classmethod
    def tearDownClass(cls):
        LLMClient.objects.filter(name__startswith=cls.resource_name_prefix).delete()
        super().tearDownClass()

    def test_clone(self):
        super().test_clone()

    def test_delete(self):
        super().test_delete()

    def test_rename(self):
        super().test_rename()

    def test_detail(self):
        super().test_detail()
