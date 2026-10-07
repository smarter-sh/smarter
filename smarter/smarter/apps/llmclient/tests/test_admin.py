"""Test the querysets of the llmclient app's ModelAdmins for LLMClient child models."""

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.admin import smarter_restricted_admin_site
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientFunctions,
    LLMClientPlugin,
)
from smarter.apps.plugin.models import PluginMeta


class TestLLMClientChildAdmins(TestAccountMixin):
    """
    Test the LLMClientPlugin and LLMClientFunctions admins.

    They list the records of the user's own LLMClients, and not those of another
    account's LLMClients.

    The non-admin user is used, because the test admin users are superusers, who may
    administer every record.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.other_admin_user, cls.other_account, cls.other_user_profile = admin_user_factory()
        cls.llmclient = LLMClient.objects.create(name="test_admin_llmclient", user_profile=cls.non_admin_user_profile)
        cls.other_llmclient = LLMClient.objects.create(
            name="test_admin_other_llmclient", user_profile=cls.other_user_profile
        )
        cls.plugin_meta = PluginMeta.objects.create(
            name="test_admin_plugin", plugin_class="static", version="1.0.0", user_profile=cls.non_admin_user_profile
        )
        cls.other_plugin_meta = PluginMeta.objects.create(
            name="test_admin_other_plugin", plugin_class="static", version="1.0.0", user_profile=cls.other_user_profile
        )
        cls.plugin = LLMClientPlugin.objects.create(llmclient=cls.llmclient, plugin_meta=cls.plugin_meta)
        cls.other_plugin = LLMClientPlugin.objects.create(
            llmclient=cls.other_llmclient, plugin_meta=cls.other_plugin_meta
        )
        cls.function = LLMClientFunctions.objects.create(llmclient=cls.llmclient, name="calculator")
        cls.other_function = LLMClientFunctions.objects.create(llmclient=cls.other_llmclient, name="calculator")

    @classmethod
    def tearDownClass(cls):
        LLMClient.objects.filter(pk__in=[cls.llmclient.pk, cls.other_llmclient.pk]).delete()
        PluginMeta.objects.filter(pk__in=[cls.plugin_meta.pk, cls.other_plugin_meta.pk]).delete()
        super().tearDownClass()

    def queryset(self, model, user):
        """Return the queryset that the ModelAdmin for ``model`` shows ``user``."""
        request = RequestFactory().get("/admin/")
        request.user = user
        return smarter_restricted_admin_site._registry[model].get_queryset(request)  # pylint: disable=W0212

    def test_llmclient_plugin_admin(self):
        """Test that the LLMClientPlugin admin lists the user's records only."""
        qs = self.queryset(LLMClientPlugin, self.non_admin_user)
        self.assertIn(self.plugin, qs)
        self.assertNotIn(self.other_plugin, qs)
        self.assertFalse(self.queryset(LLMClientPlugin, AnonymousUser()).exists())

    def test_llmclient_functions_admin(self):
        """Test that the LLMClientFunctions admin lists the user's records only."""
        qs = self.queryset(LLMClientFunctions, self.non_admin_user)
        self.assertIn(self.function, qs)
        self.assertNotIn(self.other_function, qs)
        self.assertFalse(self.queryset(LLMClientFunctions, AnonymousUser()).exists())
