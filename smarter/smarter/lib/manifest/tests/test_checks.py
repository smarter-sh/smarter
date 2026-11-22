"""Test :mod:`smarter.lib.manifest.checks`, the system checks of the SAM apps' feature flags."""

from django.core.checks import run_checks

from smarter.apps.llmclient.models import LLMClientPlugin
from smarter.apps.provider.models import Provider
from smarter.apps.proxy.models import Proxy
from smarter.common.conf import smarter_settings
from smarter.lib.manifest.checks import (
    DISABLED_APP_HAS_ROWS_ID,
    DISABLED_DEPENDENCY_ID,
    disabled_app_rows_warnings,
    disabled_dependency_warnings,
    sam_app_of_model,
)
from smarter.lib.unittest.base_classes import SmarterTestBase
from smarter.lib.unittest.sam_apps import disabled_sam_apps


class TestSamAppChecks(SmarterTestBase):
    """Test the warnings about disabled SAM apps."""

    def test_sam_app_of_model(self):
        self.assertEqual(sam_app_of_model(Proxy).app_label, "proxy")  # type: ignore[union-attr]

    def test_nothing_to_warn_about_by_default(self):
        """Test that every app is enabled by default, so there is nothing to warn about."""
        self.assertEqual(disabled_dependency_warnings(smarter_settings), [])
        self.assertEqual(disabled_app_rows_warnings(smarter_settings), [])

    def test_disabled_dependency(self):
        """Test that an enabled app's relation to a disabled app's model is a warning, with the flags to set."""
        with disabled_sam_apps("app_provider_enable", "app_llmtool_enable") as settings:
            warnings = disabled_dependency_warnings(settings)
        objects = [warning.obj for warning in warnings]
        self.assertIn(Proxy, objects)
        self.assertIn(LLMClientPlugin, objects)
        for warning in warnings:
            with self.subTest(warning=warning.msg):
                self.assertEqual(warning.id, DISABLED_DEPENDENCY_ID)
                self.assertIn("=true", str(warning.hint))

    def test_a_disabled_app_with_rows(self):
        """Test that a disabled app's rows are a warning, and an enabled app's aren't."""
        # the test database's platform has the built-in providers. See initialize_providers.
        self.assertTrue(Provider.objects.exists())
        with disabled_sam_apps("app_provider_enable") as settings:
            warnings = disabled_app_rows_warnings(settings)
        self.assertEqual([warning.id for warning in warnings], [DISABLED_APP_HAS_ROWS_ID])
        self.assertIn("Provider", warnings[0].msg)

    def test_registered(self):
        """Test that manage.py check runs the dependency check, and the rows check only with --database."""
        with disabled_sam_apps("app_provider_enable"):
            messages = run_checks()
            database_messages = run_checks(databases=["default"])
        ids = [message.id for message in messages]
        self.assertIn(DISABLED_DEPENDENCY_ID, ids)
        self.assertNotIn(DISABLED_APP_HAS_ROWS_ID, ids)
        database_ids = [message.id for message in database_messages]
        self.assertIn(DISABLED_DEPENDENCY_ID, database_ids)
