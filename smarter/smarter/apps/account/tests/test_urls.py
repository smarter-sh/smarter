# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test API end points."""

# python stuff
import os
import unittest

from django.contrib.auth import get_user_model
from django.test import Client

# our stuff
from ..models import Account, UserProfile


User = get_user_model()


class TestUrls(unittest.TestCase):
    """Test Account views."""

    user: User

    def setUp(self):
        """Set up test fixtures."""
        self.client = None
        username = "testuser_" + os.urandom(4).hex()
        self.user = User.objects.create(
            username=username, password="12345", is_staff=True, is_active=True, is_superuser=True
        )
        self.account = Account.objects.create(
            company_name="Test Company",
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )
        self.user_profile = UserProfile.objects.create(
            user=self.user,
            account=self.account,
            is_test=True,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()
        self.account.delete()
        self.user_profile.delete()

    def test_account_view(self):
        """test that we can see the account view and that it matches the account data."""
        self.client = Client()

        def verify_response(url, status_code):
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)

        verify_response("/login/", 200)
        verify_response("/logout/", 302)
        verify_response("/register/", 200)
        verify_response("/account/password-reset-request/", 200)
        verify_response("/account/password-confirm/", 200)

        self.client.force_login(self.user)
        verify_response("/account/deactivate/", 200)
