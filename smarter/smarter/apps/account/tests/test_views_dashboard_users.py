# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test User manager."""

# python stuff
import os
import unittest
from http import HTTPStatus
from urllib.parse import urlparse

from django.contrib.auth import authenticate, get_user_model
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.test import RequestFactory

# our stuff
from ..models import Account, UserProfile
from ..views.dashboard.users import UsersView, UserView


User = get_user_model()


# pylint: disable=R0902
class TestAPIKeys(unittest.TestCase):
    """Test User manager."""

    def setUp(self):
        """Set up test fixtures."""
        self.base_url = "/account/dashboard/users/"
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

    def tearDown(self):
        """Clean up test fixtures."""
        self.user_profile.delete()
        self.user.delete()
        self.account.delete()

    # pylint: disable=too-many-locals
    def test_user(self):
        """Test that we can create, update, delete a user from the dashboard views."""
        url = self.base_url + "new/"
        factory = RequestFactory()

        # test that we can create a new user
        data = {
            "username": "testuser_" + os.urandom(4).hex(),
            "password": "12345",
            "first_name": "Test",
            "last_name": "User",
            "email": "mail@mail.com",
        }
        request = factory.post(url, data=data)
        request.user = self.user

        response = UserView.as_view()(request)
        self.assertIsInstance(response, HttpResponseRedirect)

        # url should be of the form: /account/dashboard/users/649/
        url = response.url
        parsed_url = urlparse(url)
        user_id = parsed_url.path.rstrip("/").split("/")[-1]
        self.assertIsInstance(int(user_id), int)

        # test that the user matches up with the data
        # in the User model
        new_user = User.objects.get(id=user_id)
        self.assertEqual(new_user.username, data["username"])
        self.assertEqual(new_user.first_name, data["first_name"])
        self.assertEqual(new_user.last_name, data["last_name"])
        self.assertEqual(new_user.email, data["email"])

        # test that get the user view
        url = self.base_url + user_id + "/"
        request = factory.get(url)
        request.user = self.user
        response = UserView.as_view()(request, user_id=user_id)
        self.assertTrue(response.status_code, HTTPStatus.OK)
        self.assertIsInstance(response, HttpResponse)

        # test that we can update the user
        data["first_name"] = "Updated"
        request = factory.patch(url, data=data)
        request.user = self.user
        response = UserView.as_view()(request, user_id=user_id)
        self.assertIsInstance(response, JsonResponse)

        self.assertEqual(response.status_code, HTTPStatus.OK)

        updated_user = User.objects.get(id=user_id)
        self.assertEqual(updated_user.first_name, data["first_name"])

        # test that we can delete the user
        request = factory.delete(url)
        request.user = self.user
        response = UserView.as_view()(request, user_id=user_id)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_users_view(self):
        """Test that we can get the users view."""
        factory = RequestFactory()
        request = factory.get(self.base_url)
        request.user = self.user
        response = UsersView.as_view()(request)
        self.assertIsInstance(response, HttpResponse)
        self.assertEqual(response.status_code, HTTPStatus.OK)
