"""Test smarter.apps.dashboard.views.terminal_emulator.api.tickets: the terminal's single use tickets, and their api."""

from http import HTTPStatus
from unittest.mock import patch

from cache_results import lazy_cache
from django.test import Client
from django.urls import resolve

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.terminal_emulator.api import tickets
from smarter.apps.dashboard.views.terminal_emulator.api.tickets import (
    TICKET_CACHE_PREFIX,
    issue_ticket,
    redeem_ticket,
)
from smarter.apps.dashboard.views.terminal_emulator.names import (
    DashboardTerminalReverseNames,
)
from smarter.apps.dashboard.views.views.urls import DashboardReverseNames
from smarter.lib import json
from smarter.lib.django.shortcuts import reverse

ENABLED = "smarter.apps.dashboard.views.terminal_emulator.enabled.terminal_enabled"


class TestTickets(TestAccountMixin):
    """Test issue_ticket() and redeem_ticket()."""

    def test_redeemed_once_by_its_user(self):
        ticket = issue_ticket(self.admin_user.pk)
        self.assertGreaterEqual(len(ticket), 40)
        self.assertNotEqual(ticket, issue_ticket(self.admin_user.pk))
        self.assertTrue(redeem_ticket(ticket, self.admin_user.pk))
        self.assertFalse(redeem_ticket(ticket, self.admin_user.pk))

    def test_another_users_ticket_is_refused_and_spent(self):
        ticket = issue_ticket(self.admin_user.pk)
        self.assertFalse(redeem_ticket(ticket, self.non_admin_user.pk))
        self.assertFalse(redeem_ticket(ticket, self.admin_user.pk))

    def test_unknown_empty_and_long_tickets_are_refused(self):
        self.assertFalse(redeem_ticket("no-such-ticket", self.admin_user.pk))
        self.assertFalse(redeem_ticket("", self.admin_user.pk))
        self.assertFalse(redeem_ticket("x" * 200, self.admin_user.pk))

    def test_expires(self):
        with patch.object(tickets.lazy_cache, "set") as cache_set:
            ticket = issue_ticket(self.admin_user.pk)
        cache_set.assert_called_once_with(TICKET_CACHE_PREFIX + ticket, self.admin_user.pk, timeout=60)

    def test_redeemed_by_whoever_deletes_it_first(self):
        """A ticket that another request deleted between the lookup and the delete is refused."""
        ticket = issue_ticket(self.admin_user.pk)
        lazy_cache.delete(TICKET_CACHE_PREFIX + ticket)
        with patch.object(tickets.lazy_cache, "get", return_value=self.admin_user.pk):
            self.assertFalse(redeem_ticket(ticket, self.admin_user.pk))


class TestTicketApi(TestAccountMixin):
    """The ticket api issues tickets to superusers only, while the terminal is enabled."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.url = reverse(
            DashboardReverseNames.namespace,
            DashboardTerminalReverseNames.namespace,
            DashboardTerminalReverseNames.ticket,
        )

    def test_a_superuser_gets_a_ticket(self):
        self.client.force_login(self.admin_user)
        with patch(ENABLED, return_value=True):
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        body = json.loads(response.content)
        self.assertEqual(body["url"], "/ws/terminal/")
        self.assertTrue(redeem_ticket(body["ticket"], self.admin_user.pk))

    def test_not_found_for_a_user_who_is_not_a_superuser(self):
        self.client.force_login(self.non_admin_user)
        with patch(ENABLED, return_value=True):
            self.assertEqual(self.client.post(self.url).status_code, HTTPStatus.NOT_FOUND)

    def test_not_found_while_disabled(self):
        self.client.force_login(self.admin_user)
        with patch(ENABLED, return_value=False):
            self.assertEqual(self.client.post(self.url).status_code, HTTPStatus.NOT_FOUND)

    def test_an_anonymous_user_is_sent_to_sign_in(self):
        with patch(ENABLED, return_value=True):
            self.assertEqual(self.client.post(self.url).status_code, HTTPStatus.FOUND)

    def test_is_not_csrf_exempt(self):
        """The POST needs the page's CSRF token, wherever SmarterCsrfViewMiddleware checks it (not locally)."""
        self.assertFalse(getattr(resolve(self.url).func, "csrf_exempt", False))
