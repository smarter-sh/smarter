# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test API end points."""

import hashlib
import random

# python stuff
import unittest

from django.contrib.auth import get_user_model
from django.test import RequestFactory

# our stuff
from ..context_processors import base
from ..models import Account, UserProfile


User = get_user_model()


class TestContext(unittest.TestCase):
    """Test Account context processor."""

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
