"""Test :mod:`smarter.apps.secret.receivers`.

See :class:`smarter.lib.unittest.receivers.ReceiversTestMixin`.
"""

from smarter.apps.secret import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.receivers import ReceiversTestMixin


class TestSecretReceivers(ReceiversTestMixin, SmarterTestBase):
    """Call each receiver of the secret app with mock arguments."""

    receivers_module = receivers
    # these serialize the Secret model instance that the SecretTransformer holds, or query
    # the database for the user.
    skip = ("secret_saved_receiver", "secret_updated_receiver", "user_logged_in_receiver", "user_post_save")
