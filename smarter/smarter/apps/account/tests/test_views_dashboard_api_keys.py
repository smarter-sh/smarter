# pylint: disable=wrong-import-position
"""Test API Keys."""

# python stuff
import uuid
from http import HTTPStatus

from django.contrib.auth import authenticate
from django.test import RequestFactory

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.drf.models import SmarterAuthToken

from ..views.dashboard.api_keys import APIKeysView, APIKeyView


# pylint: disable=R0902
class TestAPIKeys(TestAccountMixin):
    """Test API Keys"""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.base_url = "/account/dashboard/api-keys/"
        self.username = self.non_admin_user.username
        self.password = "12345"

        self.authenticated_user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(self.authenticated_user)

        self.api_key = self.create_api_key()

        self.non_admin_user.set_password(self.password)
        self.non_admin_user.save()
        self.non_staff_authenticated_user = authenticate(username=self.non_admin_user.username, password=self.password)
        self.assertIsNotNone(self.non_staff_authenticated_user)

    def create_api_key(self):
        """Create an API Key."""
        api_key, _ = SmarterAuthToken.objects.create(
            name="testAPIKey",
            user=self.non_admin_user,
            description="Test API Key",
            is_active=True,
        )
        return api_key

    def test_get_api_key(self):
        """Test that we can get an api key."""
        url = self.base_url + str(self.api_key.key_id) + "/"
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.non_admin_user

        response = APIKeyView.as_view()(request, key_id=self.api_key.key_id)
        self.assertEqual(response.status_code, 200)

    def test_get_api_key_no_permissions(self):
        """Test that we can't get an api key without permissions."""
        another_api_key, _ = SmarterAuthToken.objects.create(
            user=self.non_admin_user,
            name=self.non_admin_user.username,
            description="ANOTHER Test API Key",
        )
        url = self.base_url + str(another_api_key) + "/"
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.non_staff_authenticated_user

        response = APIKeyView.as_view()(request, key_id=self.api_key.key_id)

        # should rediredt to login page since we're not staff
        self.assertEqual(response.status_code, 302)

    def test_get_api_key_not_found(self):
        """Test that we can't get an api key that doesn't exist."""
        nonexistent_api_key_id = str(uuid.uuid4())
        url = self.base_url + nonexistent_api_key_id + "/"
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.non_admin_user

        response = APIKeyView.as_view()(request, key_id=nonexistent_api_key_id)
        self.assertEqual(response.status_code, 404)

    def test_post_api_key_not_found(self):
        """Test that we can't get an api key that doesn't exist."""
        nonexistent_api_key_id = str(uuid.uuid4())
        url = self.base_url + nonexistent_api_key_id + "/"
        factory = RequestFactory()
        data = {}
        request = factory.post(url, data=data, content_type="application/json")
        request.user = self.non_admin_user

        response = APIKeyView.as_view()(request)
        self.assertIn(response.status_code, [302, HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST])

    def test_get_api_keys(self):
        """Test that we can get all api keys."""
        url = self.base_url
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.non_admin_user

        response = APIKeysView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_delete_nonexistent_api_key(self):
        """Test that we can't delete an api key that doesn't exist."""
        nonexistent_api_key_id = str(uuid.uuid4())
        url = self.base_url + nonexistent_api_key_id + "/"
        factory = RequestFactory()
        request = factory.delete(url)
        request.user = self.non_admin_user

        response = APIKeyView.as_view()(request, key_id=nonexistent_api_key_id)
        self.assertEqual(response.status_code, 404)
