# pylint: disable=wrong-import-position
# pylint: disable=R0801
"""Test lambda_openai_v2 function."""

import hashlib
import random

# python stuff
import unittest

from django.contrib.auth import get_user_model
from django.test import RequestFactory

# our stuff
from smarter.apps.account.models import Account, UserProfile

from ..context_processors import base, react


User = get_user_model()


class TestContextProcessor(unittest.TestCase):
    """Test Dashboard context processor."""

    def setUp(self):
        """Set up test fixtures."""
        username = "testuser" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()
        account_number = "" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()

        self.user = User.objects.create_user(username=username, password="12345")
        self.account = Account.objects.create(
            account_number=account_number, company_name="Test Company", phone_number="123-456-789"
        )
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

    # pylint: disable=broad-exception-caught
    def test_base(self):
        """Test base."""
        rf = RequestFactory()
        request = rf.get("/login/")
        request.user = self.user
        test_context = base(request=request)

        self.assertIn("dashboard", test_context)

    def test_react(self):
        """Test react."""
        rf = RequestFactory()
        request = rf.get("/login/")
        request.user = self.user
        test_context = react(request=request)

        self.assertIn("react_config", test_context)
