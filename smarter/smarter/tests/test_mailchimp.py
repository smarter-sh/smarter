# pylint: disable=wrong-import-position
"""Test User."""

# python stuff
import unittest

from smarter.common.helpers.mailchimp_helpers import MailchimpHelper


class TestMailChimp(unittest.TestCase):
    """Test Account model"""

    def test_mailchimp_is_available(self):
        """Test that Redis cache is reachable."""
        if not MailchimpHelper().ping():
            self.fail("Mailchimp API is not reachable")
