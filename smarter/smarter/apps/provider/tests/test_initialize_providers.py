"""
Test the initialize_providers management command,.

:mod:`smarter.apps.provider.management.commands.initialize_providers`.

The command creates and updates the platform's built-in Providers, which these tests must not
change, so they run its methods for a test account, with a test provider name, and with the
provider's models api mocked.
"""

import base64
import os
import tempfile
from io import StringIO
from pathlib import Path
from unittest.mock import MagicMock, patch

import requests

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.management.commands import initialize_providers
from smarter.apps.provider.management.commands.initialize_providers import Command
from smarter.apps.provider.models import Provider, ProviderModel
from smarter.apps.secret.models import Secret
from smarter.lib import json

ENV_VAR = "TEST_INITIALIZE_PROVIDERS_API_KEY"
LOGO = "logo.svg"


def models_response(status_code=200, data=None) -> MagicMock:
    response = MagicMock(status_code=status_code, text="error text")
    response.json.return_value = {"data": data if data is not None else [{"id": "model-a"}, {"id": "model-b"}, {}]}
    return response


class TestInitializeProviders(TestAccountMixin):
    """Test initialize_generic_provider(), each provider's configuration, and handle()."""

    def setUp(self):
        super().setUp()
        self.name = f"test_init_provider_{self.hash_suffix}"
        self.addCleanup(Provider.objects.filter(name=self.name).delete)
        self.addCleanup(Secret.objects.filter(user_profile=self.user_profile, name=ENV_VAR.lower()).delete)
        self.command = Command(stdout=StringIO(), stderr=StringIO())
        self.command.user_profile = self.user_profile

        # the provider's logo, which the command reads from its data/logos/<name>/ folder.
        tmp = tempfile.TemporaryDirectory()  # pylint: disable=consider-using-with
        self.addCleanup(tmp.cleanup)
        (Path(tmp.name) / "data" / "logos" / self.name).mkdir(parents=True)
        (Path(tmp.name) / "data" / "logos" / self.name / LOGO).write_text("<svg/>")
        for patcher in (
            patch.object(initialize_providers, "HERE", Path(tmp.name)),
            patch.dict(os.environ, {ENV_VAR: "sk-test-initialize"}),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def initialize(self):
        self.command.initialize_generic_provider(
            api_key_env_var=ENV_VAR,
            name=self.name,
            provider_configuration={
                "description": "a test provider",
                "base_url": "https://api.example.com/v1/",
                "default_model": "model-b",
            },
            logo_filename=LOGO,
            provider_api_url="https://example.com/keys",
        )

    def test_initialize_generic_provider(self):
        """Test that the provider, its api key secret, its logo and its models are created."""
        with patch.object(initialize_providers.requests, "get", return_value=models_response()) as get:
            self.initialize()
        self.assertEqual(get.call_args.kwargs["headers"], {"Authorization": "Bearer sk-test-initialize"})
        provider = Provider.objects.get(name=self.name)
        self.assertTrue(provider.is_active)
        self.assertEqual(provider.api_key.get_secret(), "sk-test-initialize")
        self.assertTrue(provider.logo.name.endswith(".svg"))
        models = ProviderModel.objects.filter(provider=provider)
        self.assertEqual(sorted(models.values_list("name", flat=True)), ["model-a", "model-b"])
        self.assertTrue(models.get(name="model-b").is_default)
        self.addCleanup(provider.logo.delete, save=False)

    def test_models_api_errors(self):
        """Test that the provider is created, without models, when its models api fails or has none."""
        responses = [
            requests.ConnectionError("down"),
            models_response(status_code=404),
            models_response(status_code=500),
            models_response(data=[]),
        ]
        for response in responses:
            with self.subTest(response=response):
                kwargs = {"side_effect": response} if isinstance(response, Exception) else {"return_value": response}
                with patch.object(initialize_providers.requests, "get", **kwargs):
                    self.initialize()
                provider = Provider.objects.get(name=self.name)
                self.addCleanup(provider.logo.delete, save=False)
                self.assertFalse(ProviderModel.objects.filter(provider=provider).exists())
        bad_json = models_response(status_code=500)
        bad_json.json.side_effect = ValueError("not json")
        with patch.object(initialize_providers.requests, "get", return_value=bad_json):
            self.initialize()
        self.assertIn("error text", self.command.stdout.getvalue())

    def test_no_user_profile(self):
        self.command.user_profile = None
        self.initialize()
        self.assertFalse(Provider.objects.filter(name=self.name).exists())

    def test_each_provider(self):
        """Test that each built-in provider is initialized with its own api key, configuration and logo, which exists."""
        methods = [
            "initialize_anthropic",
            "initialize_cohere",
            "initialize_fireworks",
            "initialize_googleai",
            "initialize_metaai",
            "initialize_mistral",
            "initialize_openai",
            "initialize_togetheria",
        ]
        logos = Path(initialize_providers.__file__).resolve().parent / "data" / "logos"
        with patch.object(Command, "initialize_generic_provider") as generic:
            for method in methods:
                getattr(self.command, method)()
        self.assertEqual(generic.call_count, len(methods))
        for call in generic.call_args_list:
            with self.subTest(provider=call.kwargs["name"]):
                self.assertTrue(call.kwargs["api_key_env_var"].endswith("_API_KEY"))
                self.assertTrue(call.kwargs["provider_configuration"]["base_url"].startswith("https://"))
                self.assertTrue((logos / call.kwargs["name"] / call.kwargs["logo_filename"]).exists())

    def test_google_maps(self):
        with (
            patch.object(initialize_providers, "initialize_secret") as initialize_secret,
            patch.dict(os.environ, {"GOOGLE_MAPS_API_KEY": "maps-key"}),
        ):
            self.command.initialize_google_maps()
        self.assertEqual(initialize_secret.call_args.kwargs["secret_string"], "maps-key")

    def test_google_service_account_invalid(self):
        """Test that a service account that is not base64 encoded json is not stored."""
        with patch.object(initialize_providers, "initialize_secret") as initialize_secret:
            for value in ("not base64 json", base64.b64encode(b"\xff\xfe").decode()):
                with patch.dict(os.environ, {"GOOGLE_SERVICE_ACCOUNT_B64": value}):
                    self.command.initialize_google_service_account()
        initialize_secret.assert_not_called()

    def test_google_service_account(self):
        """Test that the Google service account's json is stored as a Secret."""
        account = {"type": "service_account", "project_id": "test"}
        value = base64.b64encode(json.dumps(account).encode()).decode()
        name = initialize_providers.GOOGLE_SERVICE_ACCOUNT_SECRET_NAME
        self.addCleanup(Secret.objects.filter(user_profile=self.user_profile, name=name).delete)
        with (
            patch.dict(os.environ, {"GOOGLE_SERVICE_ACCOUNT_B64": value}),
            patch.object(
                initialize_providers, "initialize_secret", wraps=initialize_providers.initialize_secret
            ) as initialize_secret,
        ):
            self.command.initialize_google_service_account()
        stored = initialize_secret.call_args.kwargs["secret_string"]
        self.assertIsInstance(stored, str)
        self.assertEqual(json.loads(stored), account)
        secret = Secret.objects.get(user_profile=self.user_profile, name=name)
        self.assertEqual(json.loads(secret.get_secret()), account)

    def test_handle(self):
        """Test that handle() initializes each provider for the smarter admin, and reports an error."""
        methods = [
            name for name in dir(Command) if name.startswith("initialize_") and name != "initialize_generic_provider"
        ]
        patchers = [patch.object(Command, name) for name in methods]
        mocks = [patcher.start() for patcher in patchers]
        for patcher in patchers:
            self.addCleanup(patcher.stop)
        command = Command(stdout=StringIO(), stderr=StringIO())
        command.handle()
        for mock in mocks:
            mock.assert_called_once()
        mocks[0].side_effect = RuntimeError("failed")
        command.handle()
