"""Test Api v1 CLI brokers.py coverage gaps"""

from smarter.apps.account.manifest.brokers.account import SAMAccountBroker
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestApiCliV1Brokers(SmarterTestBase):
    """Test Api v1 CLI brokers.py coverage gaps"""

    def test_brokers_integrity(self):
        """test that the brokers dictionary is complete."""
        if not all(item in SAMKinds.all_values() for item in Brokers.all_brokers()):
            brokers_keys = set(Brokers.all_brokers())
            samkinds_values = set(SAMKinds.all_values())
            difference = brokers_keys.difference(samkinds_values)
            difference_list = list(difference)
            if len(difference_list) == 1:
                difference_list = difference_list[0]
            self.fail(msg=f"The following broker(s) is missing from the master BROKERS dictionary: {difference_list}")

    def test_brokers_get(self):
        """test that the correct broker is returned for the given kind."""
        account_broker = Brokers.get_broker(SAMKinds.ACCOUNT.value)
        self.assertEqual(account_broker, SAMAccountBroker)

    def test_snake_to_camel(self):
        """test that snake case strings are converted to camel case correctly."""
        self.assertEqual(Brokers.snake_to_camel("snake_case"), "snakeCase")
        self.assertEqual(Brokers.snake_to_camel("super_snake_case"), "superSnakeCase")

    def test_get_broker_kind(self):
        """
        test that the broker kind is returned correctly from the broker name
        taking into consideration spelling and case anomalies.
        """
        self.assertEqual(Brokers.get_broker_kind("Account"), SAMKinds.ACCOUNT.value)
        self.assertEqual(Brokers.get_broker_kind("account"), SAMKinds.ACCOUNT.value)
        self.assertEqual(Brokers.get_broker_kind("accounts"), SAMKinds.ACCOUNT.value)

    def test_all_brokers(self):
        """test that the full list of brokers contains all Kinds"""
        all_brokers = Brokers.all_brokers()
        all_kinds = SAMKinds.all_values()

        self.assertEqual(set(all_brokers), set(all_kinds))
