"""Test the dashboard's "My Resources" api view, :mod:`smarter.apps.dashboard.views.views.api.my_resources`."""

from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api import my_resources
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmtool.models import Extension
from smarter.lib import json
from smarter.lib.cache import lazy_cache
from smarter.lib.typing import SmarterDictType

from ..const import namespace

COUNTERS = (
    my_resources.get_pending_deployments,
    my_resources.get_llmclients,
    my_resources.get_plugins,
    my_resources.get_api_keys,
    my_resources.get_custom_domains,
    my_resources.get_mcpclients,
    my_resources.get_secrets,
    my_resources.get_providers,
    my_resources.get_guardrails,
    my_resources.get_vectorstores,
    my_resources.get_llmhosts,
    my_resources.get_extensions,
)


class TestDashboardApiViews(TestAccountMixin):
    """Test MyResourcesView and its counters."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)

    def url(self, name: str, **kwargs) -> str:
        return reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{name}", kwargs=kwargs or None)

    def my_resources(self) -> SmarterDictType:
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
        for key in (
            "pending_deployments",
            "llmclients_qty",
            "plugins_qty",
            "mcpclients_qty",
            "providers_qty",
            "guardrails_qty",
            "secrets_qty",
            "vectorstores_qty",
            "custom_domains_qty",
            "llmhosts_qty",
            "extensions_qty",
        ):
            with self.subTest(key=key):
                self.assertIsInstance(data[key], int)
        for key in ("llmclients_url", "guardrails_url", "secrets_url", "custom_domains_url", "llmhosts_url"):
            with self.subTest(key=key):
                self.assertTrue(data[key].startswith("/"))
        # the pending deployments link opens the LLMClient list, narrowed to the LLMClients that it counts.
        self.assertEqual(data["pending_deployments_url"], data["llmclients_url"] + "?filter=pending")
        self.assertEqual(data["mcpclients_url"], "/mcpclient/")
        self.assertNotIn("connections_qty", data)

    def test_my_resources_extensions_url(self):
        """Test that a superuser's Extensions link opens the console page, and anyone else's the docs."""
        self.clear_cache()
        self.assertTrue(self.my_resources()["extensions_url"].startswith("/"))
        self.client.force_login(self.non_admin_user)
        self.assertEqual(self.my_resources()["extensions_url"], my_resources.EXTENSIONS_DOCS_URL)

    def test_get_extensions(self):
        """Test that only the enabled extensions available to the user's account are counted."""
        before = my_resources.get_extensions(invalidate=True, user_profile=self.user_profile)
        suffix = self.hash_suffix.lower()
        public = Extension.objects.create(slug=f"dash-public-{suffix}", display_name="x", enabled=True)
        mine = Extension.objects.create(slug=f"dash-mine-{suffix}", display_name="x", enabled=True, all_accounts=False)
        mine.accounts.add(self.account)
        theirs = Extension.objects.create(
            slug=f"dash-theirs-{suffix}", display_name="x", enabled=True, all_accounts=False
        )
        disabled = Extension.objects.create(slug=f"dash-off-{suffix}", display_name="x")
        for extension in (public, mine, theirs, disabled):
            self.addCleanup(extension.delete)
        self.assertEqual(my_resources.get_extensions(invalidate=True, user_profile=self.user_profile), before + 2)

    def test_my_resources_anonymous(self):
        self.client.logout()
        response = self.client.post(self.url(DashboardApiReverseNames.my_resources))
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_my_resources_are_the_users_own(self):
        """Test that each user's counts are their own.

        The other user is not a superuser, because a superuser may read every LLMClient.
        """
        self.clear_cache()
        llmclient = LLMClient.objects.create(
            name=f"test_dashboard_api_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(llmclient.delete)
        mine = self.my_resources()
        other_user, other_account, other_user_profile = mortal_user_factory()
        # addCleanup runs last in, first out.
        self.addCleanup(other_account.delete)
        self.addCleanup(other_user.delete)
        self.addCleanup(other_user_profile.delete)
        self.client.force_login(other_user)
        theirs = self.my_resources()
        self.assertNotEqual(mine["llmclients_qty"], theirs["llmclients_qty"])
