"""
Test the Orchestrator /api/v1/orchestrator/ endpoints, :mod:`smarter.apps.orchestrator.api.v1`.

See :class:`smarter.lib.unittest.resource_api.ResourceApiTestMixin`.
"""

from django.urls import NoReverseMatch, reverse

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.orchestrator.api.v1.urls import OrchestratorApiV1ReverseViews
from smarter.apps.orchestrator.models import Orchestrator
from smarter.lib.unittest.resource_api import ResourceApiTestMixin


class TestOrchestratorApi(ResourceApiTestMixin, ApiV1TestBase):
    """Test the Orchestrator api."""

    model = Orchestrator
    reverse_names = OrchestratorApiV1ReverseViews
    list_view = OrchestratorApiV1ReverseViews.orchestrator_list_view
    view_by_hashed_id = OrchestratorApiV1ReverseViews.orchestrator_view_by_hashed_id
    view_by_id = OrchestratorApiV1ReverseViews.orchestrator_view_by_id
    default_api_by_hashed_id = OrchestratorApiV1ReverseViews.default_orchestrator_api_view_by_hashed_id
    id_kwarg = "orchestrator_id"
    resource_name_prefix = "test_orchestrator_api"

    @classmethod
    def create_resource(cls, name: str) -> Orchestrator:
        return Orchestrator.objects.create(name=name, user_profile=cls.user_profile)

    def test_api_is_routed(self):
        """Test that the Orchestrator api has a url."""
        try:
            reverse(f"{OrchestratorApiV1ReverseViews.namespace}:{OrchestratorApiV1ReverseViews.orchestrator_list_view}")
        except NoReverseMatch as e:
            self.fail(str(e))

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
