"""Test the dashboard's "Service Health" api view, :mod:`smarter.apps.dashboard.views.views.api.service_health`."""

from http import HTTPStatus
from unittest.mock import patch

from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api import service_health
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.common.conf import smarter_settings
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
        service_health.cached_health_checks.invalidate()
        self.addCleanup(service_health.cached_health_checks.invalidate)
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
        self.assertEqual(data["repository_url"], smarter_settings.repository_url)
        self.assertTrue(data["repository_url"].startswith("https://"))

    def test_health_checks_are_cached(self):
        """Test that the checks run once, and later requests reuse their results until the cache expires."""
        with patch.object(service_health, "run_health_checks", return_value=[{"name": "Up", "healthy": True}]) as run:
            first = json.loads(self.client.post(self.url).content)
            second = json.loads(self.client.post(self.url).content)
        self.assertEqual(run.call_count, 1)
        self.assertEqual(first["health_checks"], second["health_checks"])

    def test_refresh_runs_the_checks_again(self):
        """Test that a body of {"refresh": true} runs the checks again, rather than answering from the cache."""
        with patch.object(service_health, "run_health_checks", return_value=[{"name": "Up", "healthy": True}]) as run:
            self.client.post(self.url)
            self.client.post(self.url, data='{"refresh": true}', content_type="application/json")
            self.client.post(self.url)
        self.assertEqual(run.call_count, 2)

    def test_wants_refresh(self):
        """Test that only a JSON object whose refresh is true asks for a refresh."""
        factory = RequestFactory()
        for body, expected in [
            ('{"refresh": true}', True),
            ('{"refresh": "true"}', False),
            ('{"refresh": false}', False),
            ("{}", False),
            ("", False),
            ("not json", False),
            ("[true]", False),
            (b"\xff", False),
        ]:
            request = factory.post(self.url, data=body, content_type="application/json")
            self.assertEqual(service_health.wants_refresh(request), expected, body)

    def test_health_checks_without_a_cache(self):
        """Test that the checks still run, and report the cache down, when reading the cache raises."""
        checks = [{"name": "Cache", "healthy": False}]
        with (
            patch.object(service_health, "cached_health_checks", side_effect=ConnectionError("redis is down")),
            patch.object(service_health, "run_health_checks", return_value=checks),
        ):
            response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        self.assertEqual(json.loads(response.content)["health_checks"], checks)

    def test_service_health_anonymous(self):
        self.client.logout()
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
