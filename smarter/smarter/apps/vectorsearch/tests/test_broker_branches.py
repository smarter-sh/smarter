"""Test SAMVectorsearchBroker's not-found, not-ready and failure branches."""

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.vectorsearch.manifest.brokers.vectorsearch import (
    SAMVectorsearchBroker,
    SAMVectorsearchBrokerError,
)
from smarter.apps.vectorsearch.models import Vectorsearch
from smarter.lib.unittest.broker_branches import BrokerBranchesTestMixin, api_test_data


class TestVectorsearchBrokerBranches(BrokerBranchesTestMixin, TestAccountMixin):
    """Test the SAMVectorsearchBroker branches that the cli broker tests don't reach."""

    broker_class = SAMVectorsearchBroker
    error_class = SAMVectorsearchBrokerError
    resource_property = "vectorsearch"
    model = Vectorsearch
    manifest_path = api_test_data("vectorsearch", "vectorsearch.yaml")

    def test_resolve_vectorstore_not_found(self):
        """An unknown Vectorstore name raises the broker's error."""
        with self.assertRaises(SAMVectorsearchBrokerError):
            self.broker.resolve_vectorstore(f"no_such_vectorstore_{self.hash_suffix}")

    def test_resolve_auth_secret(self):
        """No secret name resolves to None, and an unknown one raises the broker's error."""
        self.assertIsNone(self.broker.resolve_auth_secret(None))
        with self.assertRaises(SAMVectorsearchBrokerError):
            self.broker.resolve_auth_secret(f"no_such_secret_{self.hash_suffix}")
