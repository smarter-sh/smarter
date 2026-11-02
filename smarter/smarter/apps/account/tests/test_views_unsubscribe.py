"""Test the unsubscribe page of the welcome and Slack invitation emails, as an anonymous visitor."""

from django.test import Client

from smarter.apps.account.models import AccountContact, unsubscribe_token
from smarter.apps.account.urls import AccountReverseNames
from smarter.lib.django.shortcuts import reverse

from .mixins import TestAccountMixin


class TestAccountUnsubscribeView(TestAccountMixin):
    """Test that a GET only asks, a POST unsubscribes, and a bad token is refused."""

    def setUp(self):
        super().setUp()
        self.email = f"test_unsubscribe_view_{self.hash_suffix}@example.com"
        self.contact = AccountContact(account=self.account, email=self.email, first_name="jane", welcomed=True)
        self.contact.save()
        self.addCleanup(AccountContact.objects.filter(email=self.email).delete)
        self.client = Client(enforce_csrf_checks=True)

    def url(self, token: str) -> str:
        return reverse(f"{AccountReverseNames.namespace}:{AccountReverseNames.unsubscribe}", kwargs={"token": token})

    def unsubscribed_at(self):
        return AccountContact.objects.get(pk=self.contact.pk).unsubscribed_at

    def test_url(self):
        self.assertEqual(self.url("abc"), "/account/unsubscribe/abc/")

    def test_get_asks_and_changes_nothing(self):
        response = self.client.get(self.url(unsubscribe_token(self.email)))
        self.assertEqual(response.status_code, 200)
        body = response.content.decode()
        self.assertIn(self.email, body)
        self.assertIn('method="post"', body)
        self.assertIsNone(self.unsubscribed_at())

    def test_post_unsubscribes(self):
        """Test the button, and a mail client's one-click unsubscribe, which has no CSRF token."""
        response = self.client.post(self.url(unsubscribe_token(self.email)), data={"List-Unsubscribe": "One-Click"})
        self.assertEqual(response.status_code, 200)
        self.assertIsNotNone(self.unsubscribed_at())
        self.assertNotIn('method="post"', response.content.decode())
        # a later visit says it is unsubscribed.
        response = self.client.get(self.url(unsubscribe_token(self.email)))
        self.assertNotIn('method="post"', response.content.decode())

    def test_address_without_a_contact(self):
        """Test that an address of no contact, e.g. a non-user's, is told it is unsubscribed."""
        email = f"test_unsubscribe_nobody_{self.hash_suffix}@example.com"
        response = self.client.post(self.url(unsubscribe_token(email)))
        self.assertEqual(response.status_code, 200)
        self.assertIn(email, response.content.decode())
        self.assertNotIn('method="post"', response.content.decode())

    def test_bad_token(self):
        for method in (self.client.get, self.client.post):
            with self.subTest(method=method.__name__):
                response = method(self.url(unsubscribe_token(self.email)[:-2] + "xx"))
                self.assertEqual(response.status_code, 400)
        self.assertIsNone(self.unsubscribed_at())
