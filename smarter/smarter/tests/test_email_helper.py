# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test STMPT Email Helper."""

# python stuff
import unittest

# our stuff
from smarter.email_helpers import EmailHelper


class TestSMTPEmail(unittest.TestCase):
    """Test STMPT Email Helper."""

    def setUp(self):
        """Set up test fixtures."""

    def tearDown(self):
        """Clean up test fixtures."""

    def test_email_send(self):
        """test that we can send an email."""

        EmailHelper().send_email(
            subject="test email", body="this is a test email", to="querium.co@gmail.com", html=False, from_email=None
        )
