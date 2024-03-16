# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test global context processor."""

import hashlib
import random

# python stuff
import unittest

from django.contrib.auth import get_user_model
from django.test import RequestFactory

# our stuff
from smarter.apps.account.models import Account, UserProfile
from smarter.context_processors import branding


User = get_user_model()


class TestContext(unittest.TestCase):
    """Test global context processor."""

    def setUp(self):
        """Set up test fixtures."""
        username = "testuser" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()
        account_number = "" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()

        self.user = User.objects.create_user(username=username, password="12345")
        self.account = Account.objects.create(
            account_number=account_number, company_name="Test Company", phone_number="123-456-789"
        )
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account)

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()
        self.account.delete()
        self.user_profile.delete()

    def test_context(self):
        """test that we can instantiate the context."""
        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.user
        test_context = branding(request=request)

        self.assertIn("branding", test_context)
        branding_context = test_context["branding"]
        self.assertIn("root_url", branding_context)
        self.assertIn("support_phone_number", branding_context)
        self.assertIn("corporate_name", branding_context)
        self.assertIn("support_email", branding_context)
        # asset that support_email is a valid email
        self.assertIn("@", branding_context["support_email"])
