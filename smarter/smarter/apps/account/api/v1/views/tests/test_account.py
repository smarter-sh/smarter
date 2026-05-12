# pylint: disable=wrong-import-position
"""Test AccountView and AccountListView for API end points."""

from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client
from django.urls import reverse

from smarter.apps.account.api.v1.urls import AccountAPINamespaces
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as api_namespace
from smarter.apps.api.v1.const import namespace as api_v1_namespace
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)

User = get_user_model()


class TestAccountView(TestAccountMixin):
    """Test AccountView API end point."""

    def setUp(self):
        super().setUp()
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.account_view]
        )
        self.url = reverse(self.reverse_name, args=[self.account.id])  # type: ignore

    def test_get_superuser_success(self):
        """Superuser can GET account by id."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_get_non_superuser_success(self):
        """Non-superuser get 403 response on anything."""
        self.admin_user.is_superuser = False
        self.admin_user.save()
        self.client = Client()
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_invalid_id(self):
        """GET with invalid id returns 404."""
        url = reverse(self.reverse_name, args=[999999])
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_create_account_success(self):
        """POST creates a new account and user profile."""
        data = {"name": "Test Account New Name"}
        response = self.client.post(self.url, data, content_type="application/json")
        self.assertIn(
            response.status_code,
            [HTTPStatus.FOUND, HTTPStatus.SEE_OTHER, HTTPStatus.PERMANENT_REDIRECT, HTTPStatus.TEMPORARY_REDIRECT],
        )
        # Should redirect after creation

    def test_post_invalid_data(self):
        """POST with invalid data returns 400."""
        response = self.client.post(self.url, "notjson", content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_patch_superuser_success(self):
        """Superuser can PATCH account by id."""
        patch_data = {"name": "patched_account_name"}
        response = self.client.patch(self.url, patch_data, content_type="application/json")
        self.assertIn(
            response.status_code,
            [HTTPStatus.FOUND, HTTPStatus.SEE_OTHER, HTTPStatus.PERMANENT_REDIRECT, HTTPStatus.TEMPORARY_REDIRECT],
        )
        # Should redirect after patch

    def test_patch_invalid_data(self):
        """PATCH with invalid data returns 400."""
        response = self.client.patch(self.url, "notjson", content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_patch_account_not_found(self):
        """PATCH with invalid id returns 404."""
        url = reverse(self.reverse_name, args=[999999])
        patch_data = {"name": "patched_account_name"}
        logger.debug(
            "test_patch_account_not_found() Testing PATCH with invalid account id. URL: %s, Data: %s", url, patch_data
        )
        response = self.client.patch(url, patch_data, content_type="application/json")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class TestAccountViewDeleteSuccess(TestAccountMixin):
    """Test AccountView API end point."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.account_view]
        )
        self.url = reverse(self.reverse_name, args=[self.account.id])  # type: ignore

    def test_delete_superuser_success(self):
        """Superuser can DELETE account by id."""
        self.client = Client()
        self.client.force_login(self.admin_user)
        response = self.client.delete(self.url)
        self.assertIn(
            response.status_code,
            [HTTPStatus.FOUND, HTTPStatus.SEE_OTHER, HTTPStatus.PERMANENT_REDIRECT, HTTPStatus.TEMPORARY_REDIRECT],
        )
        # Should redirect after delete


class TestAccountViewDeleteNotFound(TestAccountMixin):
    """Test AccountView API end point."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.account_view]
        )
        self.url = reverse(self.reverse_name, args=[self.account.id])  # type: ignore

    def test_delete_account_not_found(self):
        """DELETE with invalid id returns 404."""
        self.client = Client()
        self.client.force_login(self.admin_user)
        url = reverse(self.reverse_name, args=[999999])
        response = self.client.delete(url)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)


class TestAccountViewDeleteNonSuperuserForbidden(TestAccountMixin):
    """Test AccountView API end point."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.account_view]
        )
        self.url = reverse(self.reverse_name, args=[self.account.id])  # type: ignore

    def test_delete_non_superuser_forbidden(self):
        """Non-superuser cannot DELETE account by id."""
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.admin_user.is_superuser = False
        self.admin_user.save()
        self.client.force_login(self.admin_user)
        response = self.client.delete(self.url)
        self.assertIn(response.status_code, [HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN])


class TestAccountListView(TestAccountMixin):
    """Test AccountListView API end point."""

    def setUp(self):
        self.admin_user.is_superuser = True
        self.admin_user.save()
        super().setUp()
        self.client = Client()
        self.reverse_name = ":".join(
            [api_namespace, api_v1_namespace, account_namespace, AccountAPINamespaces.account_list_view]
        )
        self.url = reverse(self.reverse_name)

    def test_get_queryset_superuser(self):
        """Superuser can GET all accounts."""
        self.client = Client()
        self.client.force_login(self.admin_user)
        logger.debug("test_get_queryset_superuser() Testing GET on AccountListView with superuser. URL: %s", self.url)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_get_queryset_non_superuser(self):
        """Non-superuser gets only their account."""
        self.admin_user.is_superuser = False
        self.admin_user.save()
        self.client = Client()
        self.client.force_login(self.admin_user)
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_queryset_unauthenticated(self):
        """Unauthenticated user gets no accounts."""
        self.client.logout()
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
