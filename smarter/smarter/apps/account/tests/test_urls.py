# pylint: disable=wrong-import-position
"""Test API end points."""

from django.test import Client
from django.urls import reverse

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin


class TestUrls(TestAccountMixin):
    """Test Account views."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()

    def tearDown(self):

        if self.client is not None:
            self.client.logout()
        self.client = None
        super().tearDown()

    def test_account_view(self):
        """test that we can see the account view and that it matches the account data."""
        namespace = "account"

        def verify_response(reverse_name: str, status_code):
            url = reverse(reverse_name)
            print(f"Testing URL: {url}")
            if not self.client:
                self.fail("Client is not initialized.")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)

        verify_response(f"{namespace}:account_login", 200)
        verify_response(f"{namespace}:account_logout", 302)
        verify_response(f"{namespace}:account_register", 200)
        verify_response(f"{namespace}:account_password_reset_request", 200)
        verify_response(f"{namespace}:account_password_confirm", 200)

        if not self.client:
            self.fail("Client is not initialized.")
        self.client.force_login(self.non_admin_user)
        verify_response(f"{namespace}:account_deactivate", 200)
