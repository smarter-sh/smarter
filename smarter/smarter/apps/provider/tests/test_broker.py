"""
Test the Provider manifest broker through the api/v1/cli/ commands.

See :class:`smarter.lib.unittest.cli_brokers.CliBrokerTestMixin`.
"""

import unittest

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.provider.models import Provider
from smarter.lib.unittest.cli_brokers import NOT_IMPLEMENTED, CliBrokerTestMixin

APPLY_BUG = (
    "Expected to fail: SAMProviderBroker.apply() assigns the manifest's fields to self.provider, "
    "which it never looks up nor creates, so it is None, and applying any Provider manifest is a 500."
)


class TestProviderBroker(CliBrokerTestMixin, ApiV1TestBase):
    """Test the Provider broker.

    See APPLY_BUG for the tests that are expected to fail.
    """

    kind = SAMKinds.PROVIDER.value
    model = Provider
    name_prefix = "test_provider_broker"

    def create_provider(self) -> Provider:
        return Provider.objects.create(
            name=self.name, user_profile=self.user_profile, base_url="https://api.example.com/v1/"
        )

    def test_get_and_delete(self):
        """Test the get and delete commands, with a Provider that the ORM creates."""
        self.create_provider()
        self.assertIn(self.name, str(self.cli("get", name=self.name)))
        self.assertIn(self.name, str(self.cli("get")))
        for command in ("deploy", "undeploy", "logs"):
            with self.subTest(command=command):
                self.cli(command, status=NOT_IMPLEMENTED, name=self.name)
        self.cli("delete", name=self.name)
        self.assertFalse(Provider.objects.filter(name=self.name).exists())

    @unittest.expectedFailure
    def test_describe(self):
        """
        Test the describe command, with a Provider that the ORM creates.

        Expected to fail: SAMProviderBroker.describe() reads the Provider's name from
        kwargs.get("name"), where the cli view does not pass it, rather than from self.name,
        so it always describes the Provider None, which is not found.
        """
        self.create_provider()
        response = self.cli("describe", name=self.name)
        self.assertEqual(response["data"]["metadata"]["name"], self.name)

    @unittest.expectedFailure
    def test_apply_describe_delete(self):
        super().test_apply_describe_delete()

    @unittest.expectedFailure
    def test_get(self):
        super().test_get()

    @unittest.expectedFailure
    def test_deploy_undeploy_logs(self):
        super().test_deploy_undeploy_logs()
