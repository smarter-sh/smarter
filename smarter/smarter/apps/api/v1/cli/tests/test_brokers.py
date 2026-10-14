"""Test Api v1 CLI brokers.py coverage gaps."""

import inspect

from smarter.apps.account.manifest.brokers.account import SAMAccountBroker
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestApiCliV1Brokers(SmarterTestBase):
    """Test Api v1 CLI brokers.py coverage gaps."""

    def test_brokers_integrity(self):
        """Test that the brokers dictionary is complete."""
        if not all(item in SAMKinds.all() for item in Brokers.all_brokers()):
            brokers_keys = set(Brokers.all_brokers())
            samkinds_values = set(SAMKinds.all())
            difference = brokers_keys.difference(samkinds_values)
            difference_list = list(difference)
            if len(difference_list) == 1:
                difference_list = difference_list[0]
            self.fail(msg=f"The following broker(s) is missing from the master BROKERS dictionary: {difference_list}")

    def test_brokers_get(self):
        """Test that the correct broker is returned for the given kind."""
        account_broker = Brokers.get_broker(SAMKinds.ACCOUNT.value)
        self.assertEqual(account_broker, SAMAccountBroker)

    def test_snake_to_camel(self):
        """Test that snake case strings are converted to camel case correctly."""
        self.assertEqual(Brokers.to_camel_case("snake_case"), "snakeCase")
        self.assertEqual(Brokers.to_camel_case("super_snake_case"), "superSnakeCase")

    def test_get_broker_kind(self):
        """Test that the broker kind is returned correctly from the broker name taking into consideration spelling and case anomalies."""
        self.assertEqual(Brokers.get_broker_kind("Account"), SAMKinds.ACCOUNT.value)
        self.assertEqual(Brokers.get_broker_kind("account"), SAMKinds.ACCOUNT.value)
        self.assertEqual(Brokers.get_broker_kind("accounts"), SAMKinds.ACCOUNT.value)

    def test_all_brokers(self):
        """Test that the full list of brokers contains all Kinds."""
        all_brokers = Brokers.all_brokers()
        all_kinds = SAMKinds.all()

        self.assertEqual(set(all_brokers), set(all_kinds))

    def test_deployable_matches_deploy(self):
        """
        Test that a broker is deployable exactly when its deploy() is implemented.

        deploy() is unimplemented when it raises SAMBrokerErrorNotImplemented, as
        AbstractBroker's does; a broker that refuses with any other error would
        hide that from this test. The cli api's resources command reports each
        kind's deployable, and the smarter cli builds its deploy commands from it.
        """
        for kind in Brokers.all_brokers():
            broker_class = Brokers.get_broker(kind)
            with self.subTest(kind=kind):
                source = inspect.getsource(broker_class.deploy)
                implemented = "SAMBrokerErrorNotImplemented" not in source and "not implemented" not in source
                self.assertEqual(
                    implemented,
                    broker_class.deployable,
                    f"{broker_class.__name__}.deploy() is {'implemented' if implemented else 'not implemented'}, "
                    f"but {broker_class.__name__}.deployable is {broker_class.deployable}",
                )

    def test_deployable_kinds(self):
        """Test the kinds whose brokers deploy, so that a change to them is deliberate."""
        deployable = sorted(kind for kind in Brokers.all_brokers() if Brokers.get_broker(kind).deployable)
        self.assertEqual(
            deployable,
            sorted(
                [
                    SAMKinds.AUTH_TOKEN.value,
                    SAMKinds.CUSTOM_DOMAIN.value,
                    SAMKinds.LLM_CLIENT.value,
                    SAMKinds.LLM_HOST.value,
                    SAMKinds.LLM_HOST_COMPUTE.value,
                    SAMKinds.USER.value,
                    SAMKinds.VECTORSTORE.value,
                ]
            ),
        )
