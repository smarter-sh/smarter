"""
A test mixin that takes a manifest kind through each command of the api/v1/cli/ api, which calls the kind's broker: example-manifest, apply, get, describe, deploy, undeploy, logs and delete.

The manifest that it applies is the kind's own example manifest, renamed for the test, so the
subclass only names the kind and its Django model::

    class TestProviderBroker(CliBrokerTestMixin, ApiV1TestBase):
        kind = SAMKinds.PROVIDER.value
        model = Provider

A subclass whose example manifest needs other resources to exist, or other changes, overrides
``prepare_manifest()``.
"""

from http import HTTPStatus
from urllib.parse import urlencode

from django.db import models

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.lib.django.shortcuts import reverse
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.typing import SmarterDictType

# the statuses with which a broker answers a command that its kind does not implement. Some
# raise SAMBrokerError, a 400.
NOT_IMPLEMENTED = (HTTPStatus.OK, HTTPStatus.NOT_IMPLEMENTED, HTTPStatus.BAD_REQUEST)

# the statuses with which a broker answers a command for a resource that does not exist.
# SAMBrokerErrorNotReady is a 503.
NOT_FOUND = (HTTPStatus.NOT_FOUND, HTTPStatus.BAD_REQUEST, HTTPStatus.SERVICE_UNAVAILABLE)


class CliBrokerTestMixin:
    """
    Test a kind's broker through the api/v1/cli/ commands.

    Mix it into a test base class that provides ``hash_suffix``, ``get_response()`` and the
    :class:`unittest.TestCase` assertions, e.g. ``ApiV1TestBase``.
    """

    kind: str
    model: type[models.Model]
    name_prefix = "test_cli_broker"

    def setUp(self) -> None:
        """
        Name the test's resource, and delete the resources with that name after the test.

        The name is ``name_prefix`` plus the test class's ``hash_suffix``, so it is unique to the
        test class, and every test of the class uses the same name. The cleanup deletes every
        resource whose name starts with it.
        """
        super().setUp()  # type: ignore[misc]
        self.name = f"{self.name_prefix}_{self.hash_suffix}"  # type: ignore[attr-defined]
        self.addCleanup(self.model.objects.filter(name__startswith=self.name).delete)  # type: ignore[attr-defined]

    def cli_url(self, command: str, with_kind: bool = True, **params) -> str:
        """
        Return the url of a cli command.

        :param command: The command, e.g. ``describe``.
        :param with_kind: Whether the url includes the kind.
        :param params: Query parameters, e.g. ``name``.
        :returns: The url path, with its query string.
        """
        kwargs = None
        if with_kind:
            kwargs = {SAMKeys.KIND.value: self.kind}
        view_name = ApiV1CliReverseViews.namespace + getattr(ApiV1CliReverseViews, command)
        url = reverse(view_name, kwargs=kwargs)
        if not params:
            return url
        query_string = urlencode(params)
        return f"{url}?{query_string}"

    def cli(
        self,
        command: str,
        status: HTTPStatus | tuple[HTTPStatus, ...] = HTTPStatus.OK,
        data: SmarterDictType | None = None,
        with_kind: bool = True,
        **params,
    ) -> SmarterDictType:
        """
        Call a cli command, assert its status, which may be a tuple of statuses, and return its json.

        :param command: The command, e.g. ``apply``.
        :param status: The expected status, or a tuple of them.
        :param data: The request body, e.g. a manifest.
        :param with_kind: Whether the url includes the kind.
        :param params: Query parameters, e.g. ``name``.
        :returns: The response's json.
        """
        path = self.cli_url(command, with_kind, **params)
        response, received = self.get_response(path=path, data=data)  # type: ignore[attr-defined]
        if isinstance(status, tuple):
            statuses = status
        else:
            statuses = (status,)
        self.assertIn(received, statuses, msg=f"{command}: {response}")  # type: ignore[attr-defined]
        return response

    def example_manifest(self) -> SmarterDictType:
        """
        Return the kind's example manifest, from the ``example_manifest`` command.

        :returns: The manifest.
        """
        response = self.cli("example_manifest")
        manifest = response["data"]
        self.assertEqual(manifest[SAMKeys.KIND.value], self.kind)  # type: ignore[attr-defined]
        return manifest

    def prepare_manifest(self, manifest: SmarterDictType) -> SmarterDictType:
        """
        Return the example manifest, renamed for this test, without the status that apply ignores.

        :param manifest: The example manifest. It is changed in place.
        :returns: The manifest.
        """
        manifest[SAMKeys.METADATA.value][SAMMetadataKeys.NAME.value] = self.name
        manifest.pop(SAMKeys.STATUS.value, None)
        return manifest

    def apply(self) -> SmarterDictType:
        """
        Apply the example manifest, renamed for this test.

        :returns: The response's json.
        """
        example = self.example_manifest()
        manifest = self.prepare_manifest(example)
        response = self.cli("apply", data=manifest, with_kind=False)
        return response

    def test_example_manifest(self):
        """The example manifest is of this kind, and has a spec."""
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
        """Test that describing or deleting a resource that does not exist is refused, with a 404, 400 or 503."""
        for command in ("describe", "delete"):
            with self.subTest(command=command):  # type: ignore[attr-defined]
                self.cli(command, status=NOT_FOUND, name="no_such_resource")

    def test_deploy_undeploy_logs(self):
        """Test the commands that most kinds do not implement, which must not fail."""
        self.apply()
        for command in ("deploy", "undeploy", "logs"):
            with self.subTest(command=command):  # type: ignore[attr-defined]
                self.cli(command, status=NOT_IMPLEMENTED, name=self.name)
