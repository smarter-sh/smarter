"""
Test the dashboard's "My Resources" and "Aggregated Charges" api views,.

:mod:`smarter.apps.dashboard.views.views.api.my_resources` and
:mod:`smarter.apps.dashboard.views.views.api.charges`.
"""

import unittest
from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api import my_resources
from smarter.apps.dashboard.views.views.api.charges import AggregatedChargesPeriod
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.llmclient.models import LLMClient
from smarter.lib import json
from smarter.lib.cache import lazy_cache

from ..const import namespace

COUNTERS = (
    my_resources.get_pending_deployments,
    my_resources.get_llmclients,
    my_resources.get_plugins,
    my_resources.get_api_keys,
    my_resources.get_custom_domains,
    my_resources.get_connections,
    my_resources.get_secrets,
    my_resources.get_providers,
)


class TestDashboardApiViews(TestAccountMixin):
    """Test MyResourcesView, its counters, and ChargesView."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)

    def url(self, name: str, **kwargs) -> str:
        return reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{name}", kwargs=kwargs or None)

    def my_resources(self) -> dict:
        response = self.client.post(self.url(DashboardApiReverseNames.my_resources))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        return json.loads(response.content)

    def test_counters(self):
        """Test that each counter counts the user's resources, is cached, and is 0 without a user profile."""
        llmclient = LLMClient.objects.create(
            name=f"test_dashboard_api_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(llmclient.delete)
        for counter in COUNTERS:
            with self.subTest(counter=counter.__name__):
                count = counter(invalidate=True, user_profile=self.user_profile)
                self.assertIsInstance(count, int)
                self.assertEqual(counter(user_profile=self.user_profile), count)
                self.assertEqual(counter(user_profile=None), 0)
        self.assertGreaterEqual(my_resources.get_llmclients(invalidate=True, user_profile=self.user_profile), 1)
        self.assertGreaterEqual(
            my_resources.get_pending_deployments(invalidate=True, user_profile=self.user_profile), 1
        )

    def clear_cache(self):
        """Clear the cache, whose cached sessions include the test client's, which is then logged in again."""
        lazy_cache.clear()
        self.client.force_login(self.admin_user)

    def test_my_resources(self):
        self.clear_cache()
        data = self.my_resources()
        for key in ("pending_deployments", "llmclients_qty", "plugins_qty", "connections_qty", "providers_qty"):
            with self.subTest(key=key):
                self.assertIsInstance(data[key], int)
        self.assertTrue(data["llmclients_url"].startswith("/"))

    def test_my_resources_anonymous(self):
        self.client.logout()
        response = self.client.post(self.url(DashboardApiReverseNames.my_resources))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    @unittest.expectedFailure
    def test_my_resources_are_the_users_own(self):
        """
        Test that each user's counts are their own.

        Expected to fail: MyResourcesView.post() caches its result with @cache_results() on an
        inner function that takes no arguments, so its cache key is the same for every user,
        and every user is shown the counts of the first user who asked, until the cache expires.
        """
        self.clear_cache()
        llmclient = LLMClient.objects.create(
            name=f"test_dashboard_api_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(llmclient.delete)
        mine = self.my_resources()
        other_admin_user, _, _ = admin_user_factory()
        self.client.force_login(other_admin_user)
        theirs = self.my_resources()
        self.assertNotEqual(mine["llmclients_qty"], theirs["llmclients_qty"])

    def test_charges(self):
        """Test that the aggregated charges are returned for each periodicity."""
        periods = (
            AggregatedChargesPeriod.HOUR,
            AggregatedChargesPeriod.HALF_DAY,
            AggregatedChargesPeriod.DAY,
            AggregatedChargesPeriod.WEEK,
            AggregatedChargesPeriod.MONTH,
            AggregatedChargesPeriod.YEAR,
        )
        for periodicity in periods:
            with self.subTest(periodicity=periodicity):
                response = self.client.post(self.url(DashboardApiReverseNames.token_charges, periodicity=periodicity))
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
                json.loads(response.content)

    def test_periods(self):
        with self.assertRaises(ValueError):
            AggregatedChargesPeriod.delta("2_weeks")
        for periodicity in (AggregatedChargesPeriod.HOUR, AggregatedChargesPeriod.YEAR):
            self.assertTrue(AggregatedChargesPeriod.grouping_fields(periodicity))

    @unittest.expectedFailure
    def test_charges_unknown_periodicity(self):
        """
        Test that an unknown periodicity is a 400.

        Expected to fail: ChargesView.post() does not handle the ValueError that
        AggregatedChargesPeriod.delta() raises for an unknown periodicity, so it is a 500.
        """
        self.client.raise_request_exception = False
        response = self.client.post(self.url(DashboardApiReverseNames.token_charges, periodicity="2_weeks"))
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
