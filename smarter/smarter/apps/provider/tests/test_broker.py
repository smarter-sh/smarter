"""
Test the Provider manifest broker through the api/v1/cli/ commands.

See :class:`smarter.lib.unittest.cli_brokers.CliBrokerTestMixin`.
"""

from http import HTTPStatus
from unittest.mock import patch

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.provider.manifest.brokers.provider import (
    SAMProviderBroker,
    SAMProviderBrokerError,
)
from smarter.apps.provider.models import Provider
from smarter.apps.secret.models import Secret
from smarter.lib.unittest.cli_brokers import (
    NOT_FOUND,
    NOT_IMPLEMENTED,
    CliBrokerTestMixin,
)


class TestProviderBroker(CliBrokerTestMixin, ApiV1TestBase):
    """Test the Provider broker."""

    kind = SAMKinds.PROVIDER.value
    model = Provider
    name_prefix = "test_provider_broker"

    def setUp(self):
        super().setUp()
        # the Secret that the example manifest's api_key names.
        self.api_key = Secret.objects.create(
            name=f"test_provider_broker_key_{self.hash_suffix}",
            user_profile=self.user_profile,
            encrypted_value=Secret.encrypt("sk-secret"),
        )
        self.addCleanup(Secret.objects.filter(pk=self.api_key.pk).delete)

    def prepare_manifest(self, manifest):
        manifest = super().prepare_manifest(manifest)
        manifest["spec"]["provider"]["api_key"] = self.api_key.name
        return manifest

    def create_provider(self) -> Provider:
        return Provider.objects.create(
            name=self.name, user_profile=self.user_profile, base_url="https://api.example.com/v1/"
        )

    def test_get_and_delete(self):
        """Test the get and delete commands, with a Provider that the ORM creates."""
        self.create_provider()
        self.assertIn(self.name, str(self.cli("get", name=self.name)))
        self.assertIn(self.name, str(self.cli("get")))
        for command in ("deploy", "undeploy", "logs"):
            with self.subTest(command=command):
                self.cli(command, status=NOT_IMPLEMENTED, name=self.name)
        self.cli("delete", name=self.name)
        self.assertFalse(Provider.objects.filter(name=self.name).exists())

    def test_describe(self):
        """Test the describe command, with a Provider that the ORM creates."""
        self.create_provider()
        response = self.cli("describe", name=self.name)
        self.assertEqual(response["data"]["metadata"]["name"], self.name)

    def test_apply_describe_delete(self):
        super().test_apply_describe_delete()

    def test_get(self):
        super().test_get()

    def test_deploy_undeploy_logs(self):
        super().test_deploy_undeploy_logs()

    def test_apply_with_an_unknown_api_key(self):
        """Test that applying a Provider whose api key names no Secret is a 404, and creates nothing."""
        manifest = self.prepare_manifest(self.example_manifest())
        manifest["spec"]["provider"]["api_key"] = f"no_such_secret_{self.hash_suffix}"
        self.cli("apply", data=manifest, with_kind=False, status=NOT_FOUND)
        self.assertFalse(Provider.objects.filter(name=self.name).exists())

    def test_get_failure(self):
        """Test that a Provider that can't be converted to a manifest fails the get command."""
        self.create_provider()
        with patch.object(SAMProviderBroker, "django_orm_to_manifest_dict", side_effect=RuntimeError("broken")):
            self.cli("get", name=self.name, status=(HTTPStatus.BAD_REQUEST, HTTPStatus.INTERNAL_SERVER_ERROR))

    def test_error_message(self):
        error = SAMProviderBrokerError(message="x", thing="Provider")
        self.assertEqual(error.get_formatted_err_message, "Smarter API Provider Manifest Broker Error")
