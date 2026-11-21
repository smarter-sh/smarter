"""Test the system checks of Smarter's security middleware subclasses: :mod:`smarter.lib.django.checks`."""

from django.conf import settings
from django.core.checks import run_checks
from django.test import override_settings

from smarter.lib.django.checks import (
    CSRF_MIDDLEWARE,
    SECURITY_MIDDLEWARE,
    check_security_middleware_subclasses,
    middleware_subclass,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

SMARTER_SECURITY_MIDDLEWARE = "smarter.apps.llmclient.middleware.security.SmarterSecurityMiddleware"
SMARTER_CSRF_MIDDLEWARE = "smarter.lib.django.middleware.csrf.SmarterCsrfViewMiddleware"

# settings that pass every check that the security and CSRF middleware gate
SECURE_SETTINGS = {
    "SECURE_HSTS_SECONDS": 31536000,
    "SECURE_HSTS_INCLUDE_SUBDOMAINS": True,
    "SECURE_HSTS_PRELOAD": True,
    "SECURE_CONTENT_TYPE_NOSNIFF": True,
    "SECURE_SSL_REDIRECT": True,
    "SECURE_REFERRER_POLICY": "same-origin",
    "SECURE_CROSS_ORIGIN_OPENER_POLICY": "same-origin",
    "CSRF_COOKIE_SECURE": True,
}


def message_ids(messages) -> set[str]:
    """Return the ids of a list of check messages."""
    return {message.id for message in messages}


def without(path: str) -> list[str]:
    """Return MIDDLEWARE without one entry."""
    return [entry for entry in settings.MIDDLEWARE if entry != path]


class TestMiddlewareSubclass(SmarterTestBase):
    """Test middleware_subclass()."""

    def test_finds_smarter_subclasses(self):
        """Smarter's MIDDLEWARE has a subclass of each of Django's security middleware."""
        self.assertEqual(middleware_subclass(SECURITY_MIDDLEWARE), SMARTER_SECURITY_MIDDLEWARE)
        self.assertEqual(middleware_subclass(CSRF_MIDDLEWARE), SMARTER_CSRF_MIDDLEWARE)

    def test_finds_django_class_itself(self):
        """Django's own class counts as its subclass."""
        with override_settings(MIDDLEWARE=[CSRF_MIDDLEWARE]):
            self.assertEqual(middleware_subclass(CSRF_MIDDLEWARE), CSRF_MIDDLEWARE)

    def test_none_without_subclass(self):
        """Without a subclass in MIDDLEWARE, it returns None."""
        with override_settings(MIDDLEWARE=without(SMARTER_CSRF_MIDDLEWARE)):
            self.assertIsNone(middleware_subclass(CSRF_MIDDLEWARE))


class TestCheckSecurityMiddlewareSubclasses(SmarterTestBase):
    """Test check_security_middleware_subclasses()."""

    def test_runs_djangos_gated_checks(self):
        """With Smarter's subclasses, Django's checks of their settings run, e.g. HSTS and CSRF_COOKIE_SECURE."""
        with override_settings(SECURE_HSTS_SECONDS=0, CSRF_COOKIE_SECURE=False):
            ids = message_ids(check_security_middleware_subclasses())
        self.assertIn("security.W004", ids)
        self.assertIn("security.W016", ids)

    def test_secure_settings_pass(self):
        """With secure settings, it returns no messages."""
        with override_settings(**SECURE_SETTINGS):
            self.assertEqual(check_security_middleware_subclasses(), [])

    def test_restores_middleware(self):
        """MIDDLEWARE is unchanged after the check."""
        before = list(settings.MIDDLEWARE)
        check_security_middleware_subclasses()
        self.assertEqual(list(settings.MIDDLEWARE), before)

    def test_warns_without_security_subclass(self):
        """Without a subclass of SecurityMiddleware, it warns smarter.W001, and skips its checks."""
        with override_settings(MIDDLEWARE=without(SMARTER_SECURITY_MIDDLEWARE), SECURE_HSTS_SECONDS=0):
            ids = message_ids(check_security_middleware_subclasses())
        self.assertIn("smarter.W001", ids)
        self.assertNotIn("security.W004", ids)

    def test_warns_without_csrf_subclass(self):
        """Without a subclass of CsrfViewMiddleware, it warns smarter.W002, and skips its check."""
        with override_settings(MIDDLEWARE=without(SMARTER_CSRF_MIDDLEWARE), CSRF_COOKIE_SECURE=False):
            ids = message_ids(check_security_middleware_subclasses())
        self.assertIn("smarter.W002", ids)
        self.assertNotIn("security.W016", ids)

    def test_skips_djangos_own_class(self):
        """With Django's own class in MIDDLEWARE, Django runs its checks, so this check doesn't repeat them."""
        middleware = [*settings.MIDDLEWARE, SECURITY_MIDDLEWARE, CSRF_MIDDLEWARE]
        with override_settings(MIDDLEWARE=middleware, SECURE_HSTS_SECONDS=0, CSRF_COOKIE_SECURE=False):
            self.assertEqual(check_security_middleware_subclasses(), [])

    def test_deploy_checks(self):
        """Manage.py check --deploy reports the gated checks, and not the ones that SILENCED_SYSTEM_CHECKS silences."""
        with override_settings(SECURE_HSTS_SECONDS=0, SECURE_SSL_REDIRECT=False, CSRF_COOKIE_SECURE=False):
            # the check command reports the messages that aren't silenced, as this filter does.
            messages = run_checks(include_deployment_checks=True)
            ids = message_ids([message for message in messages if not message.is_silenced()])
        self.assertIn("security.W016", ids)
        for silenced in ("security.W001", "security.W003", "security.W004", "security.W008"):
            self.assertNotIn(silenced, ids)
