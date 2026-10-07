# pylint: disable=wrong-import-position
"""Test SAMProxyBroker, :mod:`smarter.apps.proxy.manifest.brokers.proxy`."""

import os

from pydantic import ValidationError

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.proxy.manifest.brokers.proxy import SAMProxyBroker
from smarter.apps.proxy.manifest.models.proxy.model import SAMProxy
from smarter.apps.proxy.models import Proxy
from smarter.apps.secret.models import Secret
from smarter.apps.secret.tests.factories import secret_factory
from smarter.lib import json
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
)
from smarter.lib.manifest.exceptions import SAMValidationError
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.manifest.tests.test_broker_base import TestSAMBrokerBaseClass

from .base_classes import API_KEY, BASE_URL, ProxyTestBase, get_data_path, get_test_data

PROXY_NAME = "test_proxy"


# pylint: disable=too-many-public-methods
class TestSAMProxyBroker(TestSAMBrokerBaseClass, ProxyTestBase):
    """Test the Smarter SAMProxyBroker."""

    def setUp(self):
        super().setUp()
        self._here = os.path.abspath(os.path.dirname(__file__))
        self._manifest_filespec = get_data_path("proxy.yaml")
        self.addCleanup(Proxy.objects.filter(user_profile=self.user_profile, name__startswith=PROXY_NAME).delete)

    @property
    def SAMBrokerClass(self) -> type[SAMProxyBroker]:
        return SAMProxyBroker

    @property
    def broker(self) -> SAMProxyBroker:
        return super().broker  # type: ignore

    def fresh_broker(self, manifest: dict) -> SAMProxyBroker:
        """A new broker for another manifest, without cached state."""
        return SAMProxyBroker(request=self.request, loader=SAMLoader(manifest=json.dumps(manifest)))

    def changed_manifest(self, **spec_changes) -> dict:
        """The test manifest, with parts of its spec replaced.

        A None value removes the field.
        """
        manifest = get_test_data("proxy.yaml")
        for key, value in spec_changes.items():
            if value is None:
                manifest["spec"].pop(key, None)
            else:
                manifest["spec"][key] = value
        return manifest

    def data(self, response) -> dict:
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        return json.loads(response.content)["data"]

    def get_proxy(self) -> Proxy:
        return Proxy.objects.get(user_profile=self.user_profile, name=PROXY_NAME)

    def test_registered(self):
        """Test that the CLI's broker registry knows the Proxy kind."""
        self.assertIs(Brokers.get_broker("Proxy"), SAMProxyBroker)
        self.assertIs(Brokers.get_broker("proxy"), SAMProxyBroker)

    def test_broker_initialization(self):
        self.assertTrue(self.ready)
        self.assertEqual(self.broker.kind, "Proxy")
        self.assertIs(self.broker.ORMModelClass, Proxy)
        self.assertIsInstance(self.broker.manifest, SAMProxy)
        self.assertIsNone(self.broker.proxy)

    def test_example_manifest(self):
        model = SAMProxy(**self.data(self.broker.example_manifest(self.request)))
        self.assertEqual(model.spec.auth.header, "x-api-key")

    def test_apply(self):
        """Test that apply() creates the Proxy, and resolves its Provider and Secret by name."""
        self.data(self.broker.apply(self.request))
        proxy = self.get_proxy()
        self.assertEqual((proxy.provider, proxy.api_key_secret), (self.provider, self.secret))
        self.assertEqual(proxy.base_url, BASE_URL)
        self.assertEqual((proxy.auth_header, proxy.auth_scheme), ("Authorization", "Bearer"))
        self.assertEqual(proxy.headers, {"OpenAI-Beta": "assistants=v2"})
        self.assertEqual(proxy.allowed_paths, ["chat/completions", "embeddings", "models", "models/*"])
        self.assertEqual((proxy.timeout, proxy.is_active), (30, True))
        self.assertEqual(sorted(proxy.tags_list), ["openai-compatible", "test"])
        self.assertEqual(proxy.description, "A Proxy for unit testing, to a fake OpenAI-compatible provider.")

    def test_apply_updates(self):
        """Test that applying again updates the Proxy, rather than creating another."""
        self.broker.apply(self.request)
        pk = self.get_proxy().pk
        manifest = self.changed_manifest(isActive=False, timeout=60, auth={"header": "x-api-key", "scheme": ""})
        self.fresh_broker(manifest).apply(self.request)
        self.assertEqual(Proxy.objects.filter(user_profile=self.user_profile, name=PROXY_NAME).count(), 1)
        proxy = self.get_proxy()
        self.assertEqual((proxy.pk, proxy.is_active, proxy.timeout), (pk, False, 60))
        self.assertEqual((proxy.auth_header, proxy.auth_scheme), ("x-api-key", ""))

    def test_apply_defaults(self):
        """Test that without apiKey and baseUrl, the Provider's are used."""
        self.fresh_broker(self.changed_manifest(apiKey=None, baseUrl=None)).apply(self.request)
        proxy = self.get_proxy()
        self.assertIsNone(proxy.api_key_secret)
        self.assertEqual(proxy.base_url, "")
        self.assertEqual((proxy.secret, proxy.upstream_base_url), (self.secret, BASE_URL))

    def test_apply_unknown_provider(self):
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.fresh_broker(self.changed_manifest(provider="test_proxy_no_such_provider")).apply(self.request)
        self.assertFalse(Proxy.objects.filter(user_profile=self.user_profile, name=PROXY_NAME).exists())

    def test_apply_unknown_secret(self):
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.fresh_broker(self.changed_manifest(apiKey="test_proxy_no_such_secret")).apply(self.request)

    def test_apply_account_secret(self):
        """Test that a Secret of another user of the account may be used."""
        secret = secret_factory(self.staff_user_profile, "test_broker_staff_secret", "test", "sk-staff")
        self.addCleanup(secret.delete)
        self.fresh_broker(self.changed_manifest(apiKey=secret.name)).apply(self.request)
        self.assertEqual(self.get_proxy().api_key_secret, secret)

    def test_apply_other_accounts_secret(self):
        """Test that another account's Secret is refused, even for a superuser who may read it."""
        _, other_account, other_user_profile = admin_user_factory()
        try:
            secret = secret_factory(other_user_profile, "test_broker_other_secret", "test", "sk-other")
            with self.assertRaises(SAMBrokerErrorNotFound):
                self.fresh_broker(self.changed_manifest(apiKey=secret.name)).apply(self.request)
        finally:
            Secret.objects.filter(user_profile=other_user_profile).delete()
            other_user = other_user_profile.user
            other_account.delete()
            other_user.delete()

    def test_describe(self):
        """Test that describe() returns a valid manifest, with the Secret's name, never its value."""
        self.broker.apply(self.request)
        data = self.data(SAMProxyBroker(request=self.request, loader=self.loader).describe(self.request))
        model = SAMProxy(**data)
        self.assertEqual(model.metadata.name, PROXY_NAME)
        self.assertEqual(model.spec.provider, self.provider.name)
        self.assertEqual(model.spec.apiKey, self.secret.name)
        self.assertEqual(model.spec.headers, {"OpenAI-Beta": "assistants=v2"})
        self.assertIsNotNone(model.status)
        self.assertTrue(model.status.url.endswith("/api/v1/proxy/test_proxy/"))  # type: ignore[union-attr]
        self.assertEqual(model.status.upstreamUrl, BASE_URL)  # type: ignore[union-attr]
        self.assertEqual(model.status.apiKeySecret, self.secret.name)  # type: ignore[union-attr]
        self.assertEqual(model.status.accountNumber, self.account.account_number)  # type: ignore[union-attr]
        self.assertNotIn(API_KEY, json.dumps(data))

    def test_describe_round_trip(self):
        """Test that a described manifest applies, unchanged."""
        self.broker.apply(self.request)
        data = self.data(SAMProxyBroker(request=self.request, loader=self.loader).describe(self.request))
        data.pop("status")
        before = self.get_proxy()
        self.fresh_broker(data).apply(self.request)
        after = self.get_proxy()
        for field in (
            "provider_id",
            "api_key_secret_id",
            "base_url",
            "auth_header",
            "auth_scheme",
            "headers",
            "allowed_paths",
            "timeout",
            "is_active",
        ):
            self.assertEqual(getattr(after, field), getattr(before, field), field)

    def test_describe_not_found(self):
        with self.assertRaises(SAMBrokerErrorNotFound):
            self.broker.describe(self.request)

    def test_get(self):
        self.broker.apply(self.request)
        data = self.data(self.broker.get(self.request, name=PROXY_NAME))
        items = data["data"]["items"]
        self.assertEqual([item["name"] for item in items], [PROXY_NAME])
        self.assertEqual(items[0]["providerName"], self.provider.name)
        self.assertEqual(items[0]["apiKeySecretName"], self.secret.name)
        self.assertEqual(items[0]["upstreamUrl"], BASE_URL)
        self.assertNotIn(API_KEY, json.dumps(data))

    def test_delete(self):
        self.broker.apply(self.request)
        response = SAMProxyBroker(request=self.request, loader=self.loader).delete(self.request)
        self.assertTrue(self.validate_smarter_journaled_json_response_ok(response))
        self.assertFalse(Proxy.objects.filter(user_profile=self.user_profile, name=PROXY_NAME).exists())
        # the Provider and Secret are not deleted.
        self.assertTrue(Secret.objects.filter(pk=self.secret.pk).exists())
        with self.assertRaises(SAMBrokerErrorNotFound):
            SAMProxyBroker(request=self.request, loader=self.loader).delete(self.request)

    def test_not_implemented(self):
        for method in (self.broker.deploy, self.broker.undeploy, self.broker.logs, self.broker.prompt):
            with self.subTest(method=method.__name__), self.assertRaises(SAMBrokerErrorNotImplemented):
                method(self.request)

    def test_invalid_manifest(self):
        """Test that a manifest that sets a credential header is refused."""
        with self.assertRaises((SAMValidationError, ValidationError)):
            _ = self.fresh_broker(self.changed_manifest(headers={"Authorization": "Bearer x"})).manifest
