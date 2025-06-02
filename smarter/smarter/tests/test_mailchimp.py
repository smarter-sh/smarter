# pylint: disable=wrong-import-position
"""Test User."""

from smarter.common.helpers.mailchimp_helpers import MailchimpHelper
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestMailChimp(SmarterTestBase):
    """Test Account model"""

    def test_mailchimp_is_available(self):
        """Test that Mailchimp service is reachable."""
        if not MailchimpHelper().ping():
            self.fail("Mailchimp API is not reachable")
