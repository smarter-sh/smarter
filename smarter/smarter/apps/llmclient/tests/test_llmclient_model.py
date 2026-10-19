"""Test the LLMClient model's billing, domain, mode and readiness properties, and its clone()."""

import warnings
from unittest.mock import MagicMock, patch

from django.urls import get_urlconf, set_urlconf

from smarter.apps.account.tests.factories import (
    factory_account_teardown,
    mortal_user_factory,
)
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.guardrail.tests.base_classes import GuardrailTestBase
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientExtensions,
    LLMClientGuardrails,
    LLMClientMCPClients,
    LLMClientPlugin,
)
from smarter.apps.llmtool.models import Extension, PluginMeta
from smarter.apps.mcpclient.tests.base_classes import MCPClientTestBase
from smarter.common.const import SmarterEnvironments


class TestLLMClientModel(TestAccountMixin):
    """Test LLMClient's properties, without saving changes that would deploy it."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_llmclient_model_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)

    def test_is_billable_resource(self):
        self.assertTrue(self.llmclient.is_billable_resource)

    def test_base_api_domain_in_aws(self):
        """In an AWS environment the base api domain is the environment's api domain."""
        settings = MagicMock(
            environment=list(SmarterEnvironments.aws_environments)[0], environment_api_domain="alpha.api.example.com"
        )
        with patch("smarter.apps.llmclient.models.llmclient.smarter_settings", settings):
            self.assertEqual(self.llmclient.base_api_domain, "alpha.api.example.com")

    def test_mode_of_an_unrelated_url(self):
        """A url that isn't the LLMClient's default, sandbox or custom url is of unknown mode."""
        self.assertEqual(self.llmclient.mode("https://unrelated.example.com/"), LLMClient.Modes.UNKNOWN)
        self.assertEqual(self.llmclient.mode(""), LLMClient.Modes.UNKNOWN)

    def test_ready_needs_deployment(self):
        """Outside the sandbox, a verified and certified LLMClient is ready only once deployed."""
        llmclient = self.llmclient
        llmclient.dns_verification_status = LLMClient.DnsVerificationStatusChoices.VERIFIED
        llmclient.tls_certificate_issuance_status = LLMClient.TlsCertificateIssuanceStatusChoices.ISSUED
        with patch.object(LLMClient, "mode", return_value=LLMClient.Modes.DEFAULT):
            llmclient.deployed = False
            self.assertFalse(llmclient.ready)
            llmclient.deployed = True
            self.assertTrue(llmclient.ready)

    def test_urls_on_a_deployed_llmclient_host(self):
        """The console urls build while a deployed LLMClient's urlconf is active, e.g. for its endpoints page."""
        expected = self.console_urls()
        previous = get_urlconf()
        self.addCleanup(set_urlconf, previous)
        set_urlconf("smarter.urls.llmclients")

        self.assertEqual(self.console_urls(), expected)
        self.assertIn(self.llmclient.hashed_id, expected[0])

    def console_urls(self) -> list[str]:
        """The LLMClient's urls that are reversed from the console urlconf."""
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            return [
                self.llmclient.sandbox_url,
                self.llmclient.manifest_url,
                self.llmclient.url_llmclient,
                self.llmclient.url_chat_config,
                self.llmclient.url_chatapp,
            ]


class TestLLMClientClone(MCPClientTestBase, GuardrailTestBase):
    """
    Test that LLMClient.clone() links the clone to the same plugins, MCPClients, guardrails and extensions.

    The original belongs to the non-admin user. Its plugins, MCPClient and guardrail are theirs,
    so a user of another account may not use them.
    """

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        owner = cls.non_admin_user_profile
        cls.original = LLMClient.objects.create(name=f"test_clone_{cls.hash_suffix}", user_profile=owner)
        cls.plugins = [
            PluginMeta.objects.create(
                name=f"test_clone_plugin_{i}_{cls.hash_suffix}", plugin_class="static", user_profile=owner
            )
            for i in range(2)
        ]
        for plugin in cls.plugins:
            LLMClientPlugin.objects.create(llmclient=cls.original, plugin_meta=plugin)
        cls.mcpclient_of_owner = cls.create_mcpclient(f"test_clone_mcp_{cls.hash_suffix}", user_profile=owner)
        LLMClientMCPClients.objects.create(llmclient=cls.original, mcpclient=cls.mcpclient_of_owner)
        cls.guardrail = cls.create_guardrail(f"test_clone_guardrail_{cls.hash_suffix}", user_profile=owner)
        LLMClientGuardrails.objects.create(llmclient=cls.original, guardrail=cls.guardrail)
        cls.public_extension = Extension.objects.create(
            slug=f"clone-public-{cls.hash_suffix.lower()}", display_name="x"
        )
        cls.private_extension = Extension.objects.create(
            slug=f"clone-private-{cls.hash_suffix.lower()}", display_name="x", all_accounts=False
        )
        cls.private_extension.accounts.add(cls.account)
        for extension in (cls.public_extension, cls.private_extension):
            LLMClientExtensions.objects.create(llmclient=cls.original, extension=extension)
        cls.outsider, cls.outsider_account, cls.outsider_profile = mortal_user_factory()

    @classmethod
    def tearDownClass(cls):
        LLMClient.objects.filter(name__startswith=f"test_clone_{cls.hash_suffix}").delete()
        PluginMeta.objects.filter(pk__in=[plugin.pk for plugin in cls.plugins]).delete()
        Extension.objects.filter(pk__in=[cls.public_extension.pk, cls.private_extension.pk]).delete()
        factory_account_teardown(cls.outsider, cls.outsider_account, cls.outsider_profile)
        super().tearDownClass()

    def links(self, llmclient: LLMClient) -> dict:
        """Return the names of an LLMClient's plugins, MCPClients, guardrails and extensions."""
        return {
            "plugins": sorted(link.plugin_meta.name for link in LLMClientPlugin.objects.filter(llmclient=llmclient)),
            "mcpclients": [link.mcpclient.name for link in LLMClientMCPClients.objects.filter(llmclient=llmclient)],
            "guardrails": [link.guardrail.name for link in LLMClientGuardrails.objects.filter(llmclient=llmclient)],
            "extensions": sorted(extension.slug for extension in LLMClientExtensions.extensions_for(llmclient)),
        }

    def test_clone_for_the_same_owner(self):
        """A clone for the same owner has every link, and the original keeps its own."""
        before = self.links(self.original)
        clone = self.original.clone(new_name=f"test_clone_{self.hash_suffix}_same")
        self.assertEqual(self.links(clone), before)
        self.assertEqual(len(before["plugins"]), 2)
        self.assertEqual(self.links(self.original), before)

    def test_clone_for_another_account(self):
        """A clone for a user of another account is linked only to what that user may use."""
        clone = self.original.clone(
            new_name=f"test_clone_{self.hash_suffix}_outsider", user_profile=self.outsider_profile
        )
        self.assertEqual(clone.user_profile, self.outsider_profile)
        self.assertEqual(
            self.links(clone),
            {"plugins": [], "mcpclients": [], "guardrails": [], "extensions": [self.public_extension.slug]},
        )
