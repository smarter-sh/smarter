# pylint: disable=wrong-import-position
"""Test API end points."""

from http import HTTPStatus

from django.test import Client

from smarter.apps.account.api.v1.urls import AccountAPINamespaces
from smarter.apps.account.const import namespace as account_namespace
from smarter.apps.account.models import AccountContact
from smarter.apps.api.const import namespace as api_namespace
from smarter.apps.api.v1.const import namespace as v1_namespace
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches

# our stuff
from .factories import factory_account_teardown, mortal_user_factory
from .mixins import TestAccountMixin

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.PLUGIN_LOGGING]
)


class TestUrls(TestAccountMixin):
    """Test Account API end points."""

    namespace = ":".join([api_namespace, v1_namespace, account_namespace])

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.admin_user.is_superuser = True
        self.admin_user.save()
        self.client.force_login(self.admin_user)

    def tearDown(self):

        if self.client:
            self.client.logout()

        self.client = None

        super().tearDown()

    def test_account_list_view(self):
        """Test that we can see the account view and that it matches the account data."""
        reverse_name = ":".join([self.namespace, AccountAPINamespaces.account_contact_list_view])
        response = self.client.get(reverse(reverse_name))  # type: ignore
        self.assertEqual(response.status_code, HTTPStatus.OK)

        json_data = response.json()
        self.assertIsNotNone(json_data)

    def test_account_contact_view(self):
        """Test that we can see an account from inside the list view and that it matches the account data."""

        some_contact = AccountContact.objects.first()
        reverse_name = ":".join([self.namespace, AccountAPINamespaces.account_contact_view])
        response = self.client.get(reverse(reverse_name, args=[str(some_contact.id)]))  # type: ignore

        self.assertEqual(response.status_code, HTTPStatus.OK)

        json_data = response.json()
        self.assertIsNotNone(json_data)

    def test_account_contact_delete(self):
        """Test that deleting a contact also deletes the request user's contact, found by email."""
        contact = AccountContact.objects.create(
            account=self.account,
            email=f"delete-me-{self.hash_suffix}@example.com",
            first_name="Delete",
            last_name="Me",
            welcomed=True,
        )
        user_contact, _ = AccountContact.objects.get_or_create(
            account=self.account, email=self.admin_user.email, defaults={"welcomed": True}
        )
        reverse_name = ":".join([self.namespace, AccountAPINamespaces.account_contact_view])
        try:
            response = self.client.delete(reverse(reverse_name, args=[str(contact.id)]))  # type: ignore

            self.assertEqual(response.status_code, HTTPStatus.FOUND)
            self.assertFalse(AccountContact.objects.filter(pk=contact.pk).exists())
            self.assertFalse(AccountContact.objects.filter(pk=user_contact.pk).exists())
        finally:
            AccountContact.objects.filter(pk__in=[contact.pk, user_contact.pk]).delete()

    def test_account_contact_delete_without_user_contact(self):
        """Test that nothing is deleted when the request user has no contact in the account."""
        contact = AccountContact.objects.create(
            account=self.account,
            email=f"keep-me-{self.hash_suffix}@example.com",
            first_name="Keep",
            last_name="Me",
            welcomed=True,
        )
        AccountContact.objects.filter(account=self.account, email=self.admin_user.email).delete()
        reverse_name = ":".join([self.namespace, AccountAPINamespaces.account_contact_view])
        try:
            response = self.client.delete(reverse(reverse_name, args=[str(contact.id)]))  # type: ignore

            self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
            self.assertTrue(AccountContact.objects.filter(pk=contact.pk).exists())
        finally:
            contact.delete()

    def test_account_contact_requires_superuser(self):
        """Test that a user who isn't a superuser can neither read nor delete a contact."""
        user, account, user_profile = mortal_user_factory()
        contact = AccountContact.objects.create(
            account=self.account,
            email=f"protected-{self.hash_suffix}@example.com",
            first_name="Protected",
            last_name="Contact",
            welcomed=True,
        )
        client = Client()
        client.force_login(user)
        reverse_name = ":".join([self.namespace, AccountAPINamespaces.account_contact_view])
        url = reverse(reverse_name, args=[str(contact.id)])  # type: ignore
        try:
            get_response = client.get(url)
            delete_response = client.delete(url)

            self.assertEqual(get_response.status_code, HTTPStatus.FORBIDDEN)
            self.assertEqual(delete_response.status_code, HTTPStatus.FORBIDDEN)
            self.assertTrue(AccountContact.objects.filter(pk=contact.pk).exists())
        finally:
            client.logout()
            contact.delete()
            factory_account_teardown(user=user, account=account, user_profile=user_profile)

    def test_account_users_view(self):
        """Test that we can see users associated with an account and that one of these matches the account data."""

        reverse_name = ":".join([self.namespace, AccountAPINamespaces.user_list_view])
        response = self.client.get(reverse(reverse_name))  # type: ignore

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        self.assertIsInstance(json_data, list)
        for user in json_data:
            if user.get("username") == self.admin_user.username:
                self.assertEqual(user.get("email"), self.admin_user.email)
                break

    def test_account_users_index_view(self):
        """Test that we can see an account from inside the list view and that it matches the account data."""

        reverse_name = ":".join([self.namespace, AccountAPINamespaces.user_view])
        response = self.client.get(reverse(reverse_name, args=[str(self.admin_user.id)]))  # type: ignore

        redirect_url = response.get("Location")
        msg = response.content.decode("utf-8") if redirect_url is None else redirect_url
        self.assertEqual(response.status_code, HTTPStatus.OK, msg=msg)

        json_data = response.json()
        logger.info("test_account_users_index_view json_data: %s", json_data)
        self.assertIsInstance(json_data, dict)
        self.assertEqual(json_data.get("email"), self.admin_user.email)
        self.assertEqual(json_data.get("username"), self.admin_user.username)
