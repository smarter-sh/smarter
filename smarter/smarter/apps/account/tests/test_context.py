# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test API end points."""

import hashlib
import random

# python stuff
import unittest

from django.contrib.auth.models import User
from django.test import RequestFactory

from smarter.apps.account.context_processors import base

# our stuff
from smarter.apps.account.models import Account, UserProfile


class TestContext(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

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

    def test_context(self):
        """test that we can instantiate the context."""
        rf = RequestFactory()
        request = rf.get("/login/")
        request.user = self.user
        test_context = base(request=request)

        self.assertIn("account", test_context)
        self.assertIn("account_authentication", test_context)
