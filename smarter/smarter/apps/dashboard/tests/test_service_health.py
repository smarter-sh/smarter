"""Test the dashboard's "Service Health" api view, :mod:`smarter.apps.dashboard.views.views.api.service_health`."""

from http import HTTPStatus
from unittest.mock import patch

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api import service_health
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.lib import json

from ..const import namespace


def broken_check() -> bool:
    raise ConnectionError("unreachable")


class TestServiceHealthApiView(TestAccountMixin):
    """Test ServiceHealthView and its health checks."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)
        self.url = reverse(
            f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.service_health}"
        )

    def test_database_and_cache_checks(self):
        """Test the checks of the database and the cache, which are both up while the tests run."""
        self.assertTrue(service_health.check_database())
        self.assertTrue(service_health.check_cache())

    def test_run_health_checks(self):
        """Test that a failed check, or one that raises, is unhealthy."""
        checks = {"Up": lambda: True, "Down": lambda: False, "Broken": broken_check}
        with patch.dict(service_health.HEALTH_CHECKS, checks, clear=True):
            self.assertEqual(
                service_health.run_health_checks(),
                [
                    {"name": "Up", "healthy": True},
                    {"name": "Down", "healthy": False},
                    {"name": "Broken", "healthy": False},
                ],
            )

    def test_service_health(self):
        """Test that the response has the versions, the checks, and the percentage of checks that passed."""
        checks = {"Up": lambda: True, "Down": lambda: False, "Also Up": lambda: True, "Broken": broken_check}
        with patch.dict(service_health.HEALTH_CHECKS, checks, clear=True):
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        data = json.loads(response.content)
        self.assertEqual(data["health_score"], 50)
        self.assertEqual([check["name"] for check in data["health_checks"]], list(checks))
        self.assertTrue(data["smarter_version"])

    def test_service_health_anonymous(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
