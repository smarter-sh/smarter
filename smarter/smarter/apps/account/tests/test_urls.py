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

        self.client.logout()
        self.client = None
        super().tearDown()

    def test_account_view(self):
        """test that we can see the account view and that it matches the account data."""

        def verify_response(reverse_name: str, status_code):
            url = reverse(reverse_name)
            print(f"Testing URL: {url}")
            response = self.client.get(url)
            self.assertEqual(response.status_code, status_code)

        verify_response("account_login", 200)
        verify_response("account_logout", 302)
        verify_response("account_register", 200)
        verify_response("account_password_reset_request", 200)
        verify_response("account_password_confirm", 200)

        self.client.force_login(self.non_admin_user)
        verify_response("account_deactivate", 200)
