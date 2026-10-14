"""Test the request rate limits of :mod:`smarter.lib.drf.throttling`."""

from unittest.mock import Mock, patch

from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.lib.cache import lazy_cache
from smarter.lib.drf.throttling import (
    SMARTER_THROTTLE_CLASSES,
    SmarterAnonRateThrottle,
    SmarterUserRateThrottle,
    throttle_wait,
)

MODULE = "smarter.lib.drf.throttling"

#: A documentation address, reserved by RFC 5737, so that no other test shares its counter.
CLIENT_IP = "192.0.2.17"


def rates(anon="2/minute", user="3/minute") -> Mock:
    """Return a stand-in for smarter_settings with the given throttle rates."""
    return Mock(throttle_rate_anon=anon, throttle_rate_user=user)


class TestThrottling(TestAccountMixin):
    """Test the throttle classes, and throttle_wait() for plain Django views."""

    def setUp(self):
        super().setUp()
        self.factory = RequestFactory()
        self.view = Mock()

    def tearDown(self):
        lazy_cache.delete_many(
            [
                f"throttle_anon_{CLIENT_IP}",
                f"throttle_user_{CLIENT_IP}",
                f"throttle_user_{self.non_admin_user.pk}",
            ]
        )
        super().tearDown()

    def request(self, user=None):
        request = self.factory.post("/api/v1/prompt/", REMOTE_ADDR=CLIENT_IP)
        request.user = user or AnonymousUser()
        return request

    def test_default_throttle_classes(self):
        """Test that every Django REST Framework view is throttled by the Smarter throttles."""
        self.assertEqual(
            settings.REST_FRAMEWORK["DEFAULT_THROTTLE_CLASSES"],
            [f"{cls.__module__}.{cls.__name__}" for cls in SMARTER_THROTTLE_CLASSES],
        )

    def test_rates_come_from_smarter_settings(self):
        with patch(f"{MODULE}.smarter_settings", rates()):
            self.assertEqual(SmarterAnonRateThrottle().get_rate(), "2/minute")
            self.assertEqual(SmarterUserRateThrottle().get_rate(), "3/minute")

    def test_anonymous_client_is_throttled_by_ip(self):
        """Test that an anonymous client gets the anon rate, then a wait of at least a second."""
        with patch(f"{MODULE}.smarter_settings", rates()):
            self.assertIsNone(throttle_wait(self.request(), self.view))
            self.assertIsNone(throttle_wait(self.request(), self.view))
            wait = throttle_wait(self.request(), self.view)
        self.assertIsInstance(wait, int)
        self.assertGreaterEqual(wait, 1)
        self.assertLessEqual(wait, 60)

    def test_authenticated_user_is_throttled_by_user(self):
        """Test that an authenticated user gets the user rate, and isn't limited by the anon rate."""
        with patch(f"{MODULE}.smarter_settings", rates()):
            for _ in range(3):
                self.assertIsNone(throttle_wait(self.request(user=self.non_admin_user), self.view))
            self.assertIsNotNone(throttle_wait(self.request(user=self.non_admin_user), self.view))
            # the user's requests didn't count against the anonymous client at the same address
            self.assertIsNone(throttle_wait(self.request(), self.view))

    def test_disabled_throttles(self):
        """Test that a rate of None never throttles."""
        with patch(f"{MODULE}.smarter_settings", rates(anon=None, user=None)):
            for _ in range(5):
                self.assertIsNone(throttle_wait(self.request(), self.view))
                self.assertIsNone(throttle_wait(self.request(user=self.non_admin_user), self.view))
