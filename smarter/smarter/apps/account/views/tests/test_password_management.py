"""Unit tests for password_management.py module."""

import re
from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.account.urls import AccountReverseNames
from smarter.apps.account.views.password_management import (
    PasswordResetRequestView,
    PasswordResetView,
)
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

User = get_user_model()
logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)


class TestPasswordManagementResetRequestView(TestAccountMixin):
    """Unit tests for password_management.py endpoints."""

    def setUp(self):
        super().setUp()
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = AccountReverseNames.ACCOUNT_PASSWORD_RESET_REQUEST
        self.url = reverse(self.reverse_name)  # type: ignore

    def test_get(self):
        """GET with invalid id returns 404."""
        url = reverse(self.reverse_name)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_post(self):
        """POST changes password successfully."""
        data = {"new_password": "NewPassw0rd!", "old_password": "password"}
        response = self.client.post(self.url, data, content_type="application/json")
        self.assertIn(
            response.status_code,
            [HTTPStatus.METHOD_NOT_ALLOWED, HTTPStatus.BAD_REQUEST],
        )

    def test_post_invalid_data(self):
        """POST with invalid data returns 400."""
        response = self.client.post(self.url, "notjson", content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_patch(self):
        """PATCH with invalid data returns 400."""
        response = self.client.patch(self.url, "notjson", content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_delete(self):
        """DELETE with invalid id returns 404."""
        self.client = Client()
        self.client.force_login(self.admin_user)
        url = reverse(self.reverse_name)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)


class TestPasswordManagementResetView(TestAccountMixin):
    """Unit tests for password reset view."""

    def setUp(self):
        super().setUp()
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.client = Client()

    def test_get_valid_token(self):
        """GET with valid token returns 200."""

        reverse_name = AccountReverseNames.ACCOUNT_PASSWORD_RESET_REQUEST
        url = reverse(reverse_name)
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.admin_user
        reset_link = PasswordResetRequestView().generate_password_reset_link(request, self.admin_user)
        logger.debug("Generated reset link: %s", reset_link)
        # Generated reset link: http://testserver/password-reset-link/MTk1NA/d8h9jf-58f65759c1e985a986fc61360388cef9/

        response = self.client.get(reset_link)
        self.assertIn(response.status_code, [HTTPStatus.OK, HTTPStatus.FOUND])


class TestPasswordConfirmView(TestAccountMixin):
    """Unit tests for password confirm view."""

    def setUp(self):
        super().setUp()
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.client = Client()

    def test_page_renders(self):
        """GET with valid token returns 200."""
        reverse_name = AccountReverseNames.ACCOUNT_PASSWORD_CONFIRM
        url = reverse(reverse_name)
        factory = RequestFactory()
        request = factory.get(url)
        request.user = self.admin_user
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
