"""Test the Proxy model, :mod:`smarter.apps.proxy.models`."""

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.provider.models import Provider
from smarter.apps.proxy.models import Proxy, normalize_path
from smarter.apps.secret.models import Secret
from smarter.apps.secret.tests.factories import secret_factory

from .base_classes import API_KEY, BASE_URL, ProxyTestBase


class TestNormalizePath(ProxyTestBase):
    """Test normalize_path(), which keeps paths within a Proxy's base URL."""

    def test_valid(self):
        self.assertEqual(normalize_path("/chat/completions"), "chat/completions")
        self.assertEqual(normalize_path("chat/completions"), "chat/completions")
        self.assertEqual(normalize_path("models/"), "models/")
        self.assertEqual(
            normalize_path("models/gemini-2.5-flash:generateContent"), "models/gemini-2.5-flash:generateContent"
        )
        self.assertEqual(normalize_path(""), "")
        self.assertEqual(normalize_path(None), "")

    def test_refused(self):
        for path in (
            "../admin",
            "v1/../../admin",
            "models/./x",
            "a//b",
            "models/..",
            "https://evil.example.com/",
            "a\\b",
            "%2e%2e/admin",
            "a%2Fb",
        ):
            with self.subTest(path=path):
                self.assertIsNone(normalize_path(path))


class TestProxyModel(ProxyTestBase):
    """Test the Proxy model's properties and methods."""

    def test_upstream_base_url(self):
        """Test that the base URL is the Proxy's, else the Provider's, with a trailing slash."""
        self.assertEqual(self.proxy("test_model_provider_url").upstream_base_url, BASE_URL)
        proxy = self.proxy("test_model_own_url", base_url="https://api.other-llm.com/v2")
        self.assertEqual(proxy.upstream_base_url, "https://api.other-llm.com/v2/")
        self.assertEqual(proxy.upstream_host, "api.other-llm.com")

    def test_upstream_url(self):
        proxy = self.proxy("test_model_upstream_url")
        self.assertEqual(proxy.upstream_url("/chat/completions"), BASE_URL + "chat/completions")
        self.assertEqual(proxy.upstream_url(""), BASE_URL)
        self.assertIsNone(proxy.upstream_url("../secrets"))

    def test_secret(self):
        """Test that the Secret is the Proxy's, else the Provider's, and that its value is never in its name."""
        own = secret_factory(self.user_profile, "test_model_own_secret", "test", "sk-own")
        self.addCleanup(own.delete)
        self.assertEqual(self.proxy("test_model_own_secret", api_key_secret=own).secret, own)
        fallback = self.proxy("test_model_fallback_secret", api_key_secret=None)
        self.assertEqual(fallback.secret, self.secret)
        self.assertEqual(fallback.secret_name, self.secret.name)
        self.assertNotIn(API_KEY, str(fallback.secret_name))

    def test_no_secret(self):
        provider = Provider.objects.create(
            user_profile=self.user_profile, name="test_model_keyless_provider", base_url=BASE_URL
        )
        self.addCleanup(provider.delete)
        proxy = self.proxy("test_model_no_secret", provider=provider, api_key_secret=None)
        self.assertIsNone(proxy.secret)
        self.assertIsNone(proxy.secret_name)

    def test_secret_set_null(self):
        """Test that deleting a Proxy's Secret keeps the Proxy, which falls back to the Provider's."""
        own = secret_factory(self.user_profile, "test_model_deleted_secret", "test", "sk-own")
        proxy = self.proxy("test_model_deleted_secret", api_key_secret=own)
        own.delete()
        proxy.refresh_from_db()
        self.assertIsNone(proxy.api_key_secret)
        self.assertEqual(proxy.secret, self.secret)

    def test_may_use_secret(self):
        """Test that a Proxy may use its own account's Secrets, and not another account's."""
        proxy = self.proxy("test_model_may_use_secret")
        self.assertTrue(proxy.may_use_secret(self.secret))
        mortal_secret = secret_factory(self.non_admin_user_profile, "test_model_mortal_secret", "test", "sk-x")
        self.addCleanup(mortal_secret.delete)
        self.assertTrue(proxy.may_use_secret(mortal_secret))
        self.assertFalse(proxy.may_use_secret(None))
        _, _, other_user_profile = admin_user_factory()
        other_secret = secret_factory(other_user_profile, "test_model_other_secret", "test", "sk-other")
        try:
            self.assertFalse(proxy.may_use_secret(other_secret))
        finally:
            Secret.objects.filter(user_profile=other_user_profile).delete()
            other_user_profile.account.delete()
            other_user_profile.user.delete()

    def test_is_path_allowed(self):
        proxy = self.proxy("test_model_allowed_paths")
        self.assertTrue(proxy.is_path_allowed("chat/completions"))
        self.assertTrue(proxy.is_path_allowed("/chat/completions/"))
        self.assertTrue(proxy.is_path_allowed("models"))
        self.assertTrue(proxy.is_path_allowed("models/gpt-6-luna"))
        self.assertFalse(proxy.is_path_allowed("files"))
        self.assertFalse(proxy.is_path_allowed("chat/completions/../../files"))
        self.assertFalse(proxy.is_path_allowed("fine_tuning/jobs"))
        self.assertFalse(proxy.is_path_allowed(""))

    def test_every_path_allowed(self):
        """Test that empty allowed_paths allow every path, but never one that leaves the base URL."""
        proxy = self.proxy("test_model_all_paths", allowed_paths=[])
        self.assertTrue(proxy.is_path_allowed("files"))
        self.assertTrue(proxy.is_path_allowed(""))
        self.assertFalse(proxy.is_path_allowed("../x"))

    def test_auth_header_value(self):
        self.assertEqual(self.proxy("test_model_bearer").auth_header_value("k"), "Bearer k")
        proxy = self.proxy("test_model_raw_key", auth_header="x-api-key", auth_scheme="")
        self.assertEqual(proxy.auth_header_value("k"), "k")

    def test_urls(self):
        proxy = self.proxy("test_model_urls")
        self.assertEqual(proxy.url, "/api/v1/proxy/test_model_urls/")
        self.assertEqual(proxy.manifest_url, f"/proxy/proxies/{proxy.hashed_id}/")

    def test_defaults(self):
        proxy = self.proxy("test_model_defaults")
        self.assertEqual((proxy.auth_header, proxy.auth_scheme), ("Authorization", "Bearer"))
        self.assertEqual((proxy.headers, proxy.timeout, proxy.is_active, proxy.base_url), ({}, 120, True, ""))
        self.assertTrue(proxy.is_billable_resource)
        self.assertEqual(str(proxy), "test_model_defaults")

    def test_clone(self):
        """Test that a clone copies the configuration.

        The scaffold's globally unique path made clones fail.
        """
        proxy = self.proxy("test_model_clone", headers={"anthropic-version": "2023-06-01"}, timeout=33)
        clone = proxy.clone(new_name="test_model_clone_copy", user_profile=self.non_admin_user_profile)
        self.addCleanup(Proxy.objects.filter(pk=clone.pk).delete)
        self.assertNotEqual(clone.pk, proxy.pk)
        self.assertEqual(clone.user_profile, self.non_admin_user_profile)
        self.assertEqual((clone.provider, clone.api_key_secret), (proxy.provider, proxy.api_key_secret))
        self.assertEqual((clone.headers, clone.timeout, clone.allowed_paths), (proxy.headers, 33, proxy.allowed_paths))

    def test_rename(self):
        proxy = self.proxy("test_model_rename")
        proxy.rename("test_model_renamed")
        proxy.refresh_from_db()
        self.assertEqual(proxy.name, "test_model_renamed")
        self.assertEqual(proxy.url, "/api/v1/proxy/test_model_renamed/")
