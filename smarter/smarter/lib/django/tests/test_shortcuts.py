"""Test smarter.lib.django.shortcuts."""

from django.urls import NoReverseMatch, get_urlconf, set_urlconf

from smarter.apps.account.urls import AccountReverseNames
from smarter.apps.dashboard.views.views.urls import DashboardReverseNames
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestReverse(SmarterTestBase):
    """Test the reverse() shortcut."""

    def setUp(self):
        super().setUp()
        previous = get_urlconf()
        self.addCleanup(set_urlconf, previous)

    def test_namespaces_and_view_name(self):
        """Namespaces and a view name are joined into one reverse path."""
        self.assertEqual(
            reverse(DashboardReverseNames.namespace, DashboardReverseNames.dashboard),
            reverse(f"{DashboardReverseNames.namespace}:{DashboardReverseNames.dashboard}"),
        )

    def test_active_urlconf(self):
        """Without urlconf, a console name is not found while a deployed LLMClient's urlconf is active."""
        set_urlconf("smarter.urls.llmclients")
        with self.assertRaises(NoReverseMatch):
            reverse(AccountReverseNames.ACCOUNT_PASSWORD_RESET_REQUEST)

    def test_explicit_urlconf(self):
        """An explicit urlconf is used instead of the active one."""
        set_urlconf("smarter.urls.llmclients")
        self.assertEqual(
            reverse(AccountReverseNames.ACCOUNT_PASSWORD_RESET_REQUEST, urlconf="smarter.urls.console"),
            "/password-reset-request/",
        )

    def test_explicit_urlconf_with_kwargs(self):
        """Urlconf is passed through with Django's own keyword arguments."""
        set_urlconf("smarter.urls.llmclients")
        self.assertEqual(
            reverse(AccountReverseNames.ACCOUNT_PASSWORD_RESET_REQUEST, urlconf="smarter.urls.console", kwargs={}),
            "/password-reset-request/",
        )

    def test_non_string_argument(self):
        """A non-string argument is passed through to Django's reverse()."""
        with self.assertRaises(NoReverseMatch):
            reverse(object(), urlconf="smarter.urls.console")
