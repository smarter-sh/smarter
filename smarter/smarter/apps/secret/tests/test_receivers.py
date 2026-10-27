"""Test :mod:`smarter.apps.secret.receivers`.

See :class:`smarter.lib.unittest.receivers.ReceiversTestMixin`.
"""

from unittest.mock import MagicMock, patch

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.secret import receivers
from smarter.apps.secret.tests.factories import factory_secret_teardown, secret_factory
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.receivers import ReceiversTestMixin

RECEIVERS = "smarter.apps.secret.receivers"


class TestSecretReceivers(ReceiversTestMixin, SmarterTestBase):
    """Call each receiver of the secret app with mock arguments."""

    receivers_module = receivers
    # these serialize the Secret model instance that the SecretTransformer holds.
    skip = ("secret_saved_receiver", "secret_updated_receiver")


class TestSecretLogging(TestAccountMixin):
    """Test that no receiver logs a Secret's encrypted value, which the platform's key decrypts."""

    def setUp(self):
        super().setUp()
        self.secret = secret_factory(self.user_profile, f"log_test_{self.hash_suffix}", "logging test", "plaintext")
        self.addCleanup(factory_secret_teardown, self.secret)
        self.ciphertext = bytes(self.secret.encrypted_value).decode()

    def logged(self, logger: MagicMock) -> str:
        return " ".join(str(arg) for call in logger.mock_calls for arg in call.args)

    def test_secret_log_dict(self):
        fields = receivers.secret_log_dict(self.secret)
        self.assertNotIn("encrypted_value", fields)
        self.assertEqual(fields["name"], self.secret.name)

    def test_post_save(self):
        with patch(f"{RECEIVERS}.logger") as logger:
            self.secret.save()
        self.assertIn(self.secret.name, self.logged(logger))
        self.assertNotIn(self.ciphertext, self.logged(logger))

    def test_saved_and_updated(self):
        transformer = MagicMock(secret=self.secret, id=self.secret.id)
        transformer.name = self.secret.name
        for receiver in (receivers.secret_saved_receiver, receivers.secret_updated_receiver):
            with patch(f"{RECEIVERS}.logger") as logger:
                receiver(sender=None, secret=transformer, user_profile=self.user_profile)
            self.assertIn(self.secret.name, self.logged(logger))
            self.assertNotIn(self.ciphertext, self.logged(logger))
            self.assertNotIn("encrypted_value", self.logged(logger))

    def test_one_info_line_per_apply(self):
        """Loading and saving a Secret log at DEBUG; only created or updated log at INFO."""
        transformer = MagicMock(secret=self.secret, id=self.secret.id)
        transformer.name = self.secret.name
        with patch(f"{RECEIVERS}.logger") as logger:
            receivers.secret_initializing_receiver(
                sender=None, secret_name=self.secret.name, user_profile=self.user_profile
            )
            receivers.secret_ready_receiver(sender=None, secret=transformer)
            receivers.secret_updated_receiver(sender=None, secret=transformer, user_profile=self.user_profile)
            receivers.secret_saved_receiver(sender=None, secret=transformer, user_profile=self.user_profile)
        self.assertEqual(logger.info.call_count, 1)
        self.assertIn("secret_updated()", logger.info.call_args.args[0])
        self.assertEqual(logger.info.call_args.args[3], self.secret.name)
