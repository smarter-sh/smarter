# pylint: disable=too-many-public-methods
"""
Unit tests for the WebsearchPlugin manifest models, and its domain policy.

These tests do not use the database.

.. note::

    **Experimental.** The WebsearchPlugin was designed and coded by Claude Code (Anthropic's
    Claude Opus 5.5), with Lawrence McDaniel as co-author. It is experimental, and will
    be documented.
"""

import copy
import glob
import os

from pydantic import ValidationError

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.manifest.models.websearch_plugin.const import (
    MANIFEST_KIND,
    MAX_DOMAINS,
    MAX_FETCH_CHARACTERS,
    MAX_RESULTS,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.model import (
    SAMWebsearchPlugin,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.policy import (
    DomainPolicy,
    WebsearchPolicyError,
    host_matches,
    normalize_domain,
    normalize_domains,
    url_host,
)
from smarter.apps.plugin.manifest.models.websearch_plugin.spec import (
    WebsearchData,
    WebsearchFetch,
    WebsearchSearch,
)
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
SAMPLE_PLUGINS_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "..", "data", "sample-plugins"))
TEST_DATA_PATH = os.path.abspath(os.path.join(HERE, "..", "..", "..", "plugin", "tests", "data"))

SEARCH = {"provider": "brave", "apiKey": "brave_search_api_key"}


class TestWebsearchPluginManifest(SmarterTestBase):
    """Test the WebsearchPlugin manifest models and domain policy."""

    # =========================================================================
    # registration
    # =========================================================================
    def test_kind(self):
        """Test that the manifest kind is registered."""
        self.assertEqual(MANIFEST_KIND, "WebsearchPlugin")
        self.assertEqual(SAMKinds.WEBSEARCH_PLUGIN.value, MANIFEST_KIND)
        self.assertEqual(SmarterJournalThings.WEBSEARCH_PLUGIN.value, MANIFEST_KIND)
        self.assertIn((MANIFEST_KIND, MANIFEST_KIND), SmarterJournalThings.choices())
        self.assertIn(SAMKinds.WEBSEARCH_PLUGIN, SAMKinds.all_plugins())
        self.assertIn(SAMKinds.SKILL_PLUGIN, SAMKinds.all_plugins())

    def test_kind_fits_journal(self):
        """Test that the kind fits the SAMJournal thing field."""
        self.assertLessEqual(len(MANIFEST_KIND), 24)

    # =========================================================================
    # domains
    # =========================================================================
    def test_normalize_domain(self):
        """Test domain normalization."""
        for domain, expected in (
            ("example.com", "example.com"),
            ("  Example.COM ", "example.com"),
            ("*.example.com", "example.com"),
            (".example.com", "example.com"),
            ("example.com.", "example.com"),
            ("docs.python.org", "docs.python.org"),
            ("ru", "ru"),
            ("xn--bcher-kva.example", "xn--bcher-kva.example"),
            ("bücher.example", "xn--bcher-kva.example"),
        ):
            self.assertEqual(normalize_domain(domain), expected, f"domain={domain!r}")

    def test_normalize_domain_invalid(self):
        """Test that URLs, ports, paths, wildcards and other non-domains are rejected."""
        for domain in (
            "",
            "   ",
            "https://example.com",
            "example.com/path",
            "example.com:443",
            "user@example.com",
            "exa mple.com",
            "*.*.example.com",
            "ex*ample.com",
            "-example.com",
            "example-.com",
            "a" * 64 + ".com",
            None,
            42,
        ):
            with self.assertRaises(WebsearchPolicyError, msg=f"domain={domain!r}"):
                normalize_domain(domain)  # type: ignore[arg-type]

    def test_normalize_domains(self):
        """Test that duplicate domains are removed, preserving order."""
        self.assertEqual(normalize_domains(["b.com", "A.com", "b.com", "*.a.com"]), ("b.com", "a.com"))
        self.assertEqual(normalize_domains(None), ())

    def test_normalize_domains_too_many(self):
        """Test the maximum number of domains."""
        normalize_domains([f"d{i}.com" for i in range(MAX_DOMAINS)])
        with self.assertRaises(WebsearchPolicyError):
            normalize_domains([f"d{i}.com" for i in range(MAX_DOMAINS + 1)])

    def test_policy_error_is_a_value_error(self):
        """Test that WebsearchPolicyError is a SmarterValueError."""
        self.assertTrue(issubclass(WebsearchPolicyError, SmarterValueError))

    def test_host_matches(self):
        """Test that a domain matches itself and its subdomains, but not lookalikes."""
        self.assertTrue(host_matches("python.org", "python.org"))
        self.assertTrue(host_matches("docs.python.org", "python.org"))
        self.assertTrue(host_matches("a.b.python.org", "python.org"))
        self.assertTrue(host_matches("DOCS.Python.org.", "python.org"))
        self.assertFalse(host_matches("notpython.org", "python.org"))
        self.assertFalse(host_matches("python.org.evil.com", "python.org"))
        self.assertFalse(host_matches("org", "python.org"))

    def test_url_host(self):
        """Test extracting the host of a URL."""
        self.assertEqual(url_host("https://Docs.Python.org:443/3/"), "docs.python.org")
        self.assertIsNone(url_host("not a url"))
        self.assertIsNone(url_host("https://[::1"))

    # =========================================================================
    # DomainPolicy
    # =========================================================================
    def test_policy_unrestricted(self):
        """Test that an empty policy permits every host."""
        policy = DomainPolicy.create()
        self.assertTrue(policy.permits_url("https://example.com/"))
        self.assertFalse(policy.permits_url("not a url"))
        self.assertEqual(policy.describe(), "")

    def test_policy_allowed(self):
        """Test an allow list."""
        policy = DomainPolicy.create(allowed=["python.org"])
        self.assertTrue(policy.permits_url("https://docs.python.org/3/"))
        self.assertFalse(policy.permits_url("https://example.com/"))

    def test_policy_blocked(self):
        """Test a block list."""
        policy = DomainPolicy.create(blocked=["pinterest.com"])
        self.assertFalse(policy.permits_url("https://www.pinterest.com/pin/1"))
        self.assertTrue(policy.permits_url("https://example.com/"))

    def test_policy_blocked_takes_precedence(self):
        """Test that the block list takes precedence over the allow list."""
        policy = DomainPolicy.create(allowed=["python.org"], blocked=["wiki.python.org"])
        self.assertTrue(policy.permits_url("https://docs.python.org/3/"))
        self.assertFalse(policy.permits_url("https://wiki.python.org/moin/"))

    def test_policy_describe(self):
        """Test the description of a policy for the LLM."""
        description = DomainPolicy.create(allowed=["python.org"], blocked=["wiki.python.org"]).describe()
        self.assertIn("restricted to python.org", description)
        self.assertIn("excluding wiki.python.org", description)

    def test_policy_narrow_allowed(self):
        """Test that a call can be restricted to a subset of the allowed domains."""
        policy = DomainPolicy.create(allowed=["python.org", "djangoproject.com"])
        narrowed = policy.narrow(allowed=["docs.python.org"])
        self.assertEqual(narrowed.allowed, ("docs.python.org",))
        self.assertFalse(narrowed.permits_url("https://docs.djangoproject.com/"))

    def test_policy_narrow_cannot_widen(self):
        """Test that a call cannot widen the allowed domains, nor unblock a blocked domain."""
        policy = DomainPolicy.create(allowed=["docs.python.org"], blocked=["blocked.example"])
        for allowed in (["python.org"], ["example.com"], ["docs.python.org", "evil.com"]):
            with self.assertRaises(WebsearchPolicyError, msg=f"allowed={allowed}"):
                policy.narrow(allowed=allowed)
        with self.assertRaises(WebsearchPolicyError):
            DomainPolicy.create(blocked=["blocked.example"]).narrow(allowed=["sub.blocked.example"])

    def test_policy_narrow_unrestricted(self):
        """Test that a call can restrict an unrestricted policy."""
        narrowed = DomainPolicy.create().narrow(allowed=["python.org"], blocked=["wiki.python.org"])
        self.assertEqual(narrowed.allowed, ("python.org",))
        self.assertEqual(narrowed.blocked, ("wiki.python.org",))

    def test_policy_narrow_blocked_is_additive(self):
        """Test that blocked domains requested by a call are added to the policy's blocked domains."""
        narrowed = DomainPolicy.create(blocked=["a.com"]).narrow(blocked=["b.com", "a.com"])
        self.assertEqual(narrowed.blocked, ("a.com", "b.com"))

    def test_policy_narrow_nothing(self):
        """Test that narrowing with nothing leaves the policy unchanged."""
        policy = DomainPolicy.create(allowed=["a.com"], blocked=["b.a.com"])
        self.assertEqual(policy.narrow(), policy)

    def test_policy_narrow_invalid_domain(self):
        """Test that a call with an invalid domain is rejected."""
        with self.assertRaises(WebsearchPolicyError):
            DomainPolicy.create().narrow(allowed=["https://example.com"])

    # =========================================================================
    # WebsearchSearch
    # =========================================================================
    def test_search_defaults(self):
        """Test the defaults of the search section."""
        search = WebsearchSearch(**SEARCH)
        self.assertEqual(search.maxResults, 5)
        self.assertEqual(search.safeSearch, "moderate")
        self.assertIsNone(search.country)
        self.assertIsNone(search.freshness)

    def test_search_normalizes_values(self):
        """Test that enumerated values and codes are normalized to lower case."""
        search = WebsearchSearch(
            provider="Tavily", apiKey=" key ", safeSearch="STRICT", country="US", language="EN", freshness="Week"
        )
        self.assertEqual(
            (search.provider, search.apiKey, search.safeSearch, search.country, search.language, search.freshness),
            ("tavily", "key", "strict", "us", "en", "week"),
        )

    def test_search_invalid_values(self):
        """Test that invalid search values are rejected."""
        for overrides in (
            {"provider": "google"},
            {"apiKey": ""},
            {"apiKey": "   "},
            {"safeSearch": "extreme"},
            {"country": "usa"},
            {"country": "1"},
            {"language": "english"},
            {"freshness": "hour"},
            {"maxResults": 0},
            {"maxResults": MAX_RESULTS + 1},
        ):
            with self.assertRaises((SAMValidationError, ValidationError), msg=f"overrides={overrides}"):
                WebsearchSearch(**{**SEARCH, **overrides})

    def test_search_requires_provider_and_api_key(self):
        """Test that the provider and api key are required."""
        with self.assertRaises(ValidationError):
            WebsearchSearch(provider="brave")  # type: ignore[call-arg]
        with self.assertRaises(ValidationError):
            WebsearchSearch(apiKey="key")  # type: ignore[call-arg]

    # =========================================================================
    # WebsearchFetch and WebsearchData
    # =========================================================================
    def test_fetch_defaults_and_limits(self):
        """Test the defaults and limits of the fetch section."""
        fetch = WebsearchFetch()
        self.assertEqual(fetch.maxCharacters, 20000)
        self.assertTrue(fetch.respectRobotsTxt)
        for max_characters in (999, MAX_FETCH_CHARACTERS + 1):
            with self.assertRaises(ValidationError, msg=f"maxCharacters={max_characters}"):
                WebsearchFetch(maxCharacters=max_characters)

    def test_data_requires_an_operation(self):
        """Test that at least one of search or fetch is required."""
        with self.assertRaises(SAMValidationError):
            WebsearchData()
        self.assertIsNotNone(WebsearchData(fetch=WebsearchFetch()).fetch)
        self.assertIsNotNone(WebsearchData(search=WebsearchSearch(**SEARCH)).search)

    def test_data_normalizes_domains(self):
        """Test that domains are normalized."""
        data = WebsearchData(fetch=WebsearchFetch(), allowedDomains=["*.Python.org", "python.org"], blockedDomains=None)
        self.assertEqual(data.allowedDomains, ["python.org"])
        self.assertIsNone(data.blockedDomains)
        self.assertEqual(data.domain_policy, DomainPolicy(allowed=("python.org",)))

    def test_data_invalid_domains(self):
        """Test that invalid domains are rejected."""
        with self.assertRaises(SAMValidationError):
            WebsearchData(fetch=WebsearchFetch(), allowedDomains=["https://python.org/"])

    def test_data_limits(self):
        """Test the limits of timeout and cacheTtl."""
        for overrides in ({"timeout": 0}, {"timeout": 61}, {"cacheTtl": -1}, {"cacheTtl": 86401}):
            with self.assertRaises(ValidationError, msg=f"overrides={overrides}"):
                WebsearchData(fetch=WebsearchFetch(), **overrides)
        self.assertEqual(WebsearchData(fetch=WebsearchFetch(), cacheTtl=0).cacheTtl, 0)

    # =========================================================================
    # SAMWebsearchPlugin manifests
    # =========================================================================
    def test_test_data_manifests(self):
        """Test that the unit test data manifests are valid."""
        for filename in ("websearch-plugin.yaml", "websearch-plugin-docs.yaml", "websearch-plugin-reader.yaml"):
            manifest = SAMWebsearchPlugin(**get_readonly_yaml_file(os.path.join(TEST_DATA_PATH, filename)))
            self.assertEqual(manifest.kind, MANIFEST_KIND, filename)

    def test_sample_manifests(self):
        """Test that every sample WebsearchPlugin manifest is valid."""
        paths = sorted(glob.glob(os.path.join(SAMPLE_PLUGINS_PATH, "websearch-*.yaml")))
        self.assertGreaterEqual(len(paths), 6)
        for path in paths:
            manifest = SAMWebsearchPlugin(**get_readonly_yaml_file(path))
            self.assertEqual(manifest.kind, MANIFEST_KIND, path)
            self.assertEqual(manifest.metadata.pluginClass, "websearch", path)

    def test_sample_manifests_showcase_features(self):
        """Test that the samples illustrate each feature of the WebsearchPlugin."""
        data = [
            SAMWebsearchPlugin(**get_readonly_yaml_file(path)).spec.websearchData
            for path in glob.glob(os.path.join(SAMPLE_PLUGINS_PATH, "websearch-*.yaml"))
        ]
        providers = {item.search.provider for item in data if item.search}
        self.assertEqual(providers, {"brave", "tavily"})
        self.assertTrue(any(item.fetch and not item.search for item in data), "a fetch-only sample")
        self.assertTrue(any(item.search and not item.fetch for item in data), "a search-only sample")
        self.assertTrue(any(item.allowedDomains for item in data), "an allow list sample")
        self.assertTrue(any(item.blockedDomains for item in data), "a block list sample")
        self.assertTrue(any(item.search and item.search.freshness for item in data), "a freshness sample")
        self.assertTrue(any(item.search and item.search.country for item in data), "a localized sample")

    def test_manifest_requires_websearch_data(self):
        """Test that spec.websearchData is required."""
        manifest = copy.deepcopy(get_readonly_yaml_file(os.path.join(TEST_DATA_PATH, "websearch-plugin.yaml")))
        manifest["spec"].pop("websearchData")
        with self.assertRaises(ValidationError):
            SAMWebsearchPlugin(**manifest)
