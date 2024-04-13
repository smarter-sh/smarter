# pylint: disable=wrong-import-position
"""Test API Keys."""

# python stuff
import os
import unittest
import uuid
from http import HTTPStatus

from django.contrib.auth import authenticate, get_user_model
from django.test import RequestFactory

# our stuff
from ..models import Account, APIKey, UserProfile
from ..views.dashboard.api_keys import APIKeysView, APIKeyView


User = get_user_model()


# pylint: disable=R0902
class TestAPIKeys(unittest.TestCase):
    """Test API Keys"""

    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "/account/dashboard/api-keys/"
        self.username = "testuser_" + os.urandom(4).hex()
        self.password = "12345"

        self.user = User.objects.create(username=self.username, is_staff=True, is_active=True, is_superuser=True)
        self.user.set_password(self.password)
        self.user.save()
        self.authenticated_user = authenticate(username=self.username, password=self.password)
        self.assertIsNotNone(self.authenticated_user)

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
        self.api_key = self.create_api_key()
        self.non_staff_user = User.objects.create(
            username="nonstaff_user_" + os.urandom(4).hex(),
            is_staff=False,
            is_active=True,
            is_superuser=False,
        )

        self.non_staff_user.set_password(self.password)
        self.non_staff_user.save()
        self.non_staff_authenticated_user = authenticate(username=self.non_staff_user.username, password=self.password)
        self.assertIsNotNone(self.non_staff_authenticated_user)

        self.non_staff_account = Account.objects.create(
            company_name="A Non Staff Test Company",
            phone_number="1234567890",
            address1="123 Test St",
            address2="Apt 1",
            city="Test City",
            state="TX",
            postal_code="12345",
        )

        self.non_staff_user_profile = UserProfile.objects.create(
            user=self.non_staff_user,
            account=self.non_staff_account,
            is_test=True,
        )

    def tearDown(self):
        """Clean up test fixtures."""
        self.user_profile.delete()
        self.user.delete()
        self.account.delete()
        self.api_key.delete()
        self.non_staff_user_profile.delete()
        self.non_staff_user.delete()
        self.non_staff_account.delete()

    def create_api_key(self):
        """Create an API Key."""
        api_key, _ = APIKey.objects.create(
            user=self.user,
            description="Test API Key",
            is_active=True,
        )
        return api_key

    # pylint: disable=too-many-locals
    # def test_api_key(self):
    #     """Test that we can create, update, delete an api key."""
    #     SUCCESS_CODES = [302, HTTPStatus.CREATED, HTTPStatus.OK, HTTPStatus.PERMANENT_REDIRECT, HTTPStatus.TEMPORARY_REDIRECT]
    #     description = "TEST KEY" + "_" + str(time.time())

    #     url = self.base_url + "new/"
    #     factory = RequestFactory()

    #     # test that we can create an api key
    #     data = {
    #         "description": description,
    #         "is_active": True,
    #     }
    #     request = factory.post(url, data=data)
    #     request.user = self.user

    #     # should redirect to the api key detail page
    #     response = APIKeyView.as_view()(request)
    #     self.assertIn(response.status_code, SUCCESS_CODES)
    #     api_key = APIKey.objects.get(description=description)

    #     # test that we can activate an api key
    #     factory = RequestFactory()
    #     data = {"action": "activate"}
    #     url = self.base_url + api_key.key_id + "/"
    #     request_activate = factory.patch(url, data=JsonResponse(data).content, content_type="application/json")
    #     request_activate.user = self.user
    #     response_activate = APIKeyView.as_view()(request_activate)
    #     self.assertIn(response_activate.status_code, SUCCESS_CODES)

    #     # test that we can deactivate an api key
    #     factory = RequestFactory()
    #     data = {"action": "deactivate"}
    #     url = self.base_url + api_key.key_id + "/"
    #     request_deactivate = factory.patch(url, data=JsonResponse(data).content, content_type="application/json")
    #     request_deactivate.user = self.user
    #     response_deactivate = APIKeyView.as_view()(request_deactivate)
    #     self.assertIn(response_deactivate.status_code, SUCCESS_CODES)

    #     deactivated_api_key = APIKey.objects.get(key_id=api_key.key_id)
    #     self.assertFalse(deactivated_api_key.is_active)

    #     # test that we can delete an api key
    #     factory = RequestFactory()
    #     url = self.base_url + api_key.key_id + "/"
    #     request_delete = factory.delete(url)
    #     request_delete.user = self.user
    #     response_delete = APIKeyView.as_view()(request_delete)
    #     self.assertIn(response_delete.status_code, SUCCESS_CODES)

    def test_get_api_key(self):
        """Test that we can get an api key."""
        url = self.base_url + str(self.api_key.key_id) + "/"
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.user

        response = APIKeyView.as_view()(request, key_id=self.api_key.key_id)
        self.assertEqual(response.status_code, 200)

    def test_get_api_key_no_permissions(self):
        """Test that we can't get an api key without permissions."""
        another_api_key, _ = APIKey.objects.create(
            user=self.user,
            description="ANOTHER Test API Key",
            is_active=True,
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
        request.user = self.user

        response = APIKeyView.as_view()(request, key_id=nonexistent_api_key_id)
        self.assertEqual(response.status_code, 404)

    def test_post_api_key_not_found(self):
        """Test that we can't get an api key that doesn't exist."""
        nonexistent_api_key_id = str(uuid.uuid4())
        url = self.base_url + nonexistent_api_key_id + "/"
        factory = RequestFactory()
        data = {}
        request = factory.post(url, data=data, content_type="application/json")
        request.user = self.user

        response = APIKeyView.as_view()(request)
        self.assertIn(response.status_code, [302, HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST])

    def test_get_api_keys(self):
        """Test that we can get all api keys."""
        url = self.base_url
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.user

        response = APIKeysView.as_view()(request)
        self.assertEqual(response.status_code, 200)

    def test_delete_nonexistent_api_key(self):
        """Test that we can't delete an api key that doesn't exist."""
        nonexistent_api_key_id = str(uuid.uuid4())
        url = self.base_url + nonexistent_api_key_id + "/"
        factory = RequestFactory()
        request = factory.delete(url)
        request.user = self.user

        response = APIKeyView.as_view()(request, key_id=nonexistent_api_key_id)
        self.assertEqual(response.status_code, 404)
