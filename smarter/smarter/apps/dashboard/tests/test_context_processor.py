# pylint: disable=wrong-import-position
# pylint: disable=R0801
"""Test lambda_openai_v2 function."""

from django.conf import settings
from django.test import RequestFactory
from django.urls import get_urlconf, set_urlconf

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.urls import DashboardReverseNames

from ..context_processors import base, console_reverse, sidebar_context


class TestContextProcessor(TestAccountMixin):
    """Test Dashboard context processor."""

    # pylint: disable=broad-exception-caught
    def test_base(self):
        """Test base."""
        rf = RequestFactory()
        request = rf.get("/login/")
        request.user = self.non_admin_user
        test_context = base(request=request)

        self.assertIn("dashboard", test_context)

    def test_sidebar_on_a_deployed_llmclient_host(self):
        """The sidebar reverses console names even while a deployed LLMClient's urlconf is active."""
        sidebar_context.invalidate()
        self.addCleanup(sidebar_context.invalidate)
        previous = get_urlconf()
        self.addCleanup(set_urlconf, previous)
        set_urlconf("smarter.urls.llmclients")

        context = sidebar_context()

        self.assertEqual(
            context["sidebar"]["dashboard"],
            console_reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard),
        )
        self.assertTrue(context["sidebar"]["secrets"].startswith("/"))

    def test_console_reverse_ignores_the_active_urlconf(self):
        """Console_reverse() resolves against settings.ROOT_URLCONF."""
        expected = console_reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard)
        previous = get_urlconf()
        self.addCleanup(set_urlconf, previous)
        set_urlconf("smarter.urls.llmclients")

        self.assertEqual(console_reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard), expected)
        self.assertEqual(settings.ROOT_URLCONF, "smarter.urls.console")
