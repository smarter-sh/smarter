"""
Test the Orchestrator dashboard views: the React list page, its list, clone, delete and rename api, and the manifest detail page.

See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.orchestrator.api.web.urls import OrchestratorApiWebReverseNames
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
    web_reverse_names = OrchestratorApiWebReverseNames
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

    def test_web_api_paths(self):
        """Test that the list page's endpoints are in the web console's api."""
        self.assertEqual(self.web_url("listview_all"), "/api/web/orchestrator/listview/")
        self.assertEqual(self.web_url("listview", ownership_filter="owned"), "/api/web/orchestrator/listview/owned/")
        self.assertEqual(self.web_id_url("clone", 1, new_name="x"), "/api/web/orchestrator/clone/1/x/")
        self.assertEqual(self.web_id_url("rename", 1, new_name="x"), "/api/web/orchestrator/rename/1/x/")
        self.assertEqual(self.web_id_url("delete", 1), "/api/web/orchestrator/delete/1/")

    def test_clone(self):
        super().test_clone()

    def test_delete(self):
        super().test_delete()

    def test_rename(self):
        super().test_rename()

    def test_detail(self):
        super().test_detail()
