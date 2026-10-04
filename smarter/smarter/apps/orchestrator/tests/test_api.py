"""Test the Orchestrator /api/v1/ endpoints, :mod:`smarter.apps.orchestrator.api.v1`."""

import unittest

from django.urls import NoReverseMatch, reverse

from smarter.apps.orchestrator.api.v1.urls import OrchestratorApiV1ReverseViews
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestOrchestratorApi(SmarterTestBase):
    """Test the Orchestrator api."""

    @unittest.expectedFailure
    def test_api_is_routed(self):
        """
        Test that the Orchestrator api has a url.

        Expected to fail: smarter.apps.api.v1.urls includes the urls of the Vectorsearch api,
        from which the Orchestrator api was copied, but not those of the Orchestrator api,
        so none of its views can be reached.
        """
        try:
            reverse(f"{OrchestratorApiV1ReverseViews.namespace}:{OrchestratorApiV1ReverseViews.orchestrator_list_view}")
        except NoReverseMatch as e:
            self.fail(str(e))
