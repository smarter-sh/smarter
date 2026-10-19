"""Test :mod:`smarter.hosts`: the django-hosts patterns that route a request's host to a urlconf."""

from django_hosts.resolvers import get_host_patterns

from smarter.common.conf import smarter_settings
from smarter.common.const import SmarterEnvironments
from smarter.lib.unittest.base_classes import SmarterTestBase

API_DOMAIN = smarter_settings.root_api_domain


def matching_host(hostname: str):
    """The first host pattern that matches the hostname, as django-hosts resolves it, or None."""
    for pattern in get_host_patterns():
        if pattern.compiled_regex.match(hostname):
            return pattern
    return None


def urlconf_name(pattern) -> str:
    """The dotted name of a host pattern's urlconf, which smarter.hosts passes as a module."""
    return getattr(pattern.urlconf, "__name__", pattern.urlconf)


class TestHostPatterns(SmarterTestBase):
    """Test that deployed LLMClients' hosts are routed to smarter.urls.llmclients."""

    def test_deployed_llmclient_hosts(self):
        for prefix in (
            "",
            f"{SmarterEnvironments.ALPHA}.",
            f"{SmarterEnvironments.BETA}.",
            f"{SmarterEnvironments.NEXT}.",
        ):
            hostname = f"stackademy-sql.3141-5926-5359.{prefix}{API_DOMAIN}"
            with self.subTest(hostname=hostname):
                pattern = matching_host(hostname)
                self.assertIsNotNone(pattern, hostname)
                self.assertEqual(urlconf_name(pattern), "smarter.urls.llmclients")
                match = pattern.compiled_regex.match(hostname)
                self.assertEqual(match.group("llmclient_name"), "stackademy-sql")
                self.assertEqual(match.group("account_number"), "3141-5926-5359")

    def test_other_hosts_are_not_llmclients(self):
        for hostname in (
            # a two-part account number, and a dot that isn't one.
            f"stackademy.3141-5926.{API_DOMAIN}",
            f"stackademy.3141-5926-5359.{API_DOMAIN.replace('.', 'x', 1)}",
            f"stackademy.3141-5926-5359.example.com",
            # the api domain without the platform subdomain.
            f"stackademy.3141-5926-5359.{smarter_settings.api_subdomain}.{smarter_settings.root_domain}",
        ):
            with self.subTest(hostname=hostname):
                pattern = matching_host(hostname)
                self.assertTrue(pattern is None or urlconf_name(pattern) != "smarter.urls.llmclients", hostname)
