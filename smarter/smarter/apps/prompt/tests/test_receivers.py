"""Test :mod:`smarter.apps.prompt.receivers`.

See :class:`smarter.lib.unittest.receivers.ReceiversTestMixin`.
"""

from smarter.apps.prompt import receivers
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.receivers import ReceiversTestMixin


class TestPromptReceivers(ReceiversTestMixin, SmarterTestBase):
    """Call each receiver of the prompt app with mock arguments."""

    receivers_module = receivers
    # these serialize a real request, or read attributes of the sending provider instance.
    skip = (
        "handle_chat_completion_response_received",
        "handle_chat_response_success",
        "handle_chat_provider_initialized",
    )
