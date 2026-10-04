"""
A test mixin that takes a manifest kind through each command of the api/v1/cli/ api, which.

calls the kind's broker: example-manifest, apply, get, describe, deploy, undeploy, logs and
delete.

The manifest that it applies is the kind's own example manifest, renamed for the test, so the
subclass only names the kind and its Django model::

    class TestProviderBroker(CliBrokerTestMixin, ApiV1TestBase):
        kind = SAMKinds.PROVIDER.value
        model = Provider

A subclass whose example manifest needs other resources to exist, or other changes, overrides
prepare_manifest().
"""

from http import HTTPStatus
from typing import Any
from urllib.parse import urlencode

from django.db import models

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.lib.django.shortcuts import reverse
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys

# the statuses with which a broker answers a command that its kind does not implement. Some
# raise SAMBrokerError, a 400.
NOT_IMPLEMENTED = (HTTPStatus.OK, HTTPStatus.NOT_IMPLEMENTED, HTTPStatus.BAD_REQUEST)

# the statuses with which a broker answers a command for a resource that does not exist.
# SAMBrokerErrorNotReady is a 503.
NOT_FOUND = (HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST, HTTPStatus.SERVICE_UNAVAILABLE)


class CliBrokerTestMixin:
    """Test a kind's broker through the api/v1/cli/ commands."""

    kind: str
    model: type[models.Model]
    name_prefix = "test_cli_broker"

    def setUp(self):
        super().setUp()  # type: ignore[misc]
        self.name = f"{self.name_prefix}_{self.hash_suffix}"  # type: ignore[attr-defined]
        self.addCleanup(self.model.objects.filter(name__startswith=self.name).delete)  # type: ignore[attr-defined]

    def cli_url(self, command: str, with_kind: bool = True, **params) -> str:
        kwargs = {SAMKeys.KIND.value: self.kind} if with_kind else None
        url = reverse(ApiV1CliReverseViews.namespace + getattr(ApiV1CliReverseViews, command), kwargs=kwargs)
        return f"{url}?{urlencode(params)}" if params else url

    def cli(self, command: str, status=HTTPStatus.OK, data=None, with_kind: bool = True, **params) -> dict:
        """Call a cli command, assert its status, which may be a tuple of statuses, and return its json."""
        response, received = self.get_response(path=self.cli_url(command, with_kind, **params), data=data)  # type: ignore[attr-defined]
        statuses = status if isinstance(status, tuple) else (status,)
        self.assertIn(received, statuses, msg=f"{command}: {response}")  # type: ignore[attr-defined]
        return response

    def example_manifest(self) -> dict[str, Any]:
        response = self.cli("example_manifest")
        manifest = response["data"]
        self.assertEqual(manifest[SAMKeys.KIND.value], self.kind)  # type: ignore[attr-defined]
        return manifest

    def prepare_manifest(self, manifest: dict[str, Any]) -> dict[str, Any]:
        """Return the example manifest, renamed for this test, without the status that apply ignores."""
        manifest[SAMKeys.METADATA.value][SAMMetadataKeys.NAME.value] = self.name
        manifest.pop(SAMKeys.STATUS.value, None)
        return manifest

    def apply(self) -> dict:
        manifest = self.prepare_manifest(self.example_manifest())
        return self.cli("apply", data=manifest, with_kind=False)

    def test_example_manifest(self):
        manifest = self.example_manifest()
        self.assertIn(SAMKeys.SPEC.value, manifest)  # type: ignore[attr-defined]

    def test_apply_describe_delete(self):
        """Test that the example manifest is applied, described, applied again, which updates it, and deleted."""
        self.apply()
        self.assertTrue(self.model.objects.filter(name=self.name).exists())  # type: ignore[attr-defined]

        response = self.cli("describe", name=self.name)
        self.assertEqual(response["data"][SAMKeys.METADATA.value][SAMMetadataKeys.NAME.value], self.name)  # type: ignore[attr-defined]

        self.apply()

        self.cli("delete", name=self.name)
        self.assertFalse(self.model.objects.filter(name=self.name).exists())  # type: ignore[attr-defined]

    def test_get(self):
        """Test that get lists the applied resource, by name and among all of them."""
        self.apply()
        self.assertIn(self.name, str(self.cli("get", name=self.name)))  # type: ignore[attr-defined]
        self.assertIn(self.name, str(self.cli("get")))  # type: ignore[attr-defined]

    def test_unknown_name(self):
        """Test that describing or deleting a resource that does not exist is refused, as brokers do, with a 503."""
        for command in ("describe", "delete"):
            with self.subTest(command=command):  # type: ignore[attr-defined]
                self.cli(command, status=NOT_FOUND, name="no_such_resource")

    def test_deploy_undeploy_logs(self):
        """Test the commands that most kinds do not implement, which must not fail."""
        self.apply()
        for command in ("deploy", "undeploy", "logs"):
            with self.subTest(command=command):  # type: ignore[attr-defined]
                self.cli(command, status=NOT_IMPLEMENTED, name=self.name)
