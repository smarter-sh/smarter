"""
Test the cli's get, describe and apply views, for every kind, as a client of the api sees them.

These are the contracts that the Python SDK, smarter-python, relies on:

- ``get`` answers 200 for every kind, with or without a name.
- ``get ?name=`` returns only the resources of that name.
- ``describe`` of a name that ``get`` listed returns that resource, with the same name.
- ``describe`` of a missing resource answers 404, not 503 or 400.
- ``get`` of a plugin kind returns only the plugins of that kind, and ``describe`` of a plugin with
  another kind's endpoint answers 404, not 500.
- ``apply`` returns the resource's api version, kind and name, and none of the broker's internals.
"""

import os
from http import HTTPStatus
from typing import Optional
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.secret.models import Secret
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)
from smarter.lib.typing import SmarterDictType

from .base_class import ApiV1CliTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
MISSING_NAME = "zz_no_such_resource"


class TestGetAndDescribeEveryKind(ApiV1CliTestBase):
    """Get and describe every kind through the cli api."""

    def url(self, view: str, kind: Optional[str] = None, **params) -> str:
        """The url of a cli view, with its query parameters."""
        path = reverse(self.namespace + view, kwargs={SAMKeys.KIND.value: kind} if kind else None)
        return f"{path}?{urlencode(params)}" if params else path

    def get(self, kind: str, **params) -> tuple[SmarterDictType, int]:
        """The response of get, and its status."""
        return self.get_response(path=self.url(ApiV1CliReverseViews.get, kind, **params))

    @staticmethod
    def items(response: SmarterDictType) -> list[SmarterDictType]:
        """The items of a get response."""
        return response[SCLIResponseGet.DATA.value][SCLIResponseGet.DATA.value][SCLIResponseGetData.ITEMS.value]

    def test_get_every_kind(self):
        """Test that get answers 200 for every kind, including Account and SqlConnection, which answered 503."""
        for kind in Brokers.all_brokers():
            with self.subTest(kind=kind):
                response, status = self.get(kind)
                self.assertEqual(status, HTTPStatus.OK, response)
                data = response[SCLIResponseGet.DATA.value]
                self.assertEqual(data[SAMKeys.METADATA.value]["count"], len(self.items(response)))

    def test_get_by_missing_name_every_kind(self):
        """Test that get honors ?name=, which it used to ignore, returning every resource."""
        for kind in Brokers.all_brokers():
            with self.subTest(kind=kind):
                response, status = self.get(kind, name=MISSING_NAME)
                self.assertEqual(status, HTTPStatus.OK, response)
                self.assertEqual(self.items(response), [], f"get {kind} ?name={MISSING_NAME} returned resources")

    def test_get_by_name_every_kind(self):
        """Test that get ?name= returns only the resources of that name, for every kind that has some."""
        for kind in Brokers.all_brokers():
            response, _ = self.get(kind)
            names = [item[SAMMetadataKeys.NAME.value] for item in self.items(response) if item.get("name")]
            if not names:
                continue
            with self.subTest(kind=kind, name=names[0]):
                response, status = self.get(kind, name=names[0])
                self.assertEqual(status, HTTPStatus.OK, response)
                items = self.items(response)
                self.assertTrue(items)
                self.assertEqual({item[SAMMetadataKeys.NAME.value] for item in items}, {names[0]})

    def test_describe_what_get_lists(self):
        """Test that describe returns the resources that get lists, by the same name."""
        for kind in Brokers.all_brokers():
            response, _ = self.get(kind)
            names = [item[SAMMetadataKeys.NAME.value] for item in self.items(response) if item.get("name")]
            for name in names[:3]:
                with self.subTest(kind=kind, name=name):
                    response, status = self.get_response(path=self.url(ApiV1CliReverseViews.describe, kind, name=name))
                    self.assertEqual(status, HTTPStatus.OK, response)
                    metadata = response[SCLIResponseGet.DATA.value][SAMKeys.METADATA.value]
                    self.assertEqual(metadata[SAMMetadataKeys.NAME.value], name)

    def test_describe_missing_every_kind(self):
        """Test that describe of a missing resource answers 404 for every kind."""
        for kind in Brokers.all_brokers():
            with self.subTest(kind=kind):
                response, status = self.get_response(
                    path=self.url(ApiV1CliReverseViews.describe, kind, name=MISSING_NAME)
                )
                self.assertEqual(status, HTTPStatus.NOT_FOUND, response)
                self.assertEqual(response["error"]["errorClass"], "SAMBrokerErrorNotFound")


class TestPluginKinds(ApiV1CliTestBase):
    """Test that each plugin kind's get and describe see only the plugins of that kind."""

    plugin_name = "cli_test_plugin"

    def url(self, view: str, kind: Optional[str] = None, **params) -> str:
        """The url of a cli view, with its query parameters."""
        path = reverse(self.namespace + view, kwargs={SAMKeys.KIND.value: kind} if kind else None)
        return f"{path}?{urlencode(params)}" if params else path

    def setUp(self):
        super().setUp()
        manifest = self.get_readonly_yaml_file(os.path.join(HERE, "data", "good-plugin-manifest.yaml"))
        response, status = self.get_response(self.url(ApiV1CliReverseViews.apply), manifest=manifest)  # type: ignore[arg-type]
        self.assertEqual(status, HTTPStatus.OK, response)
        self.addCleanup(
            lambda: PluginMeta.objects.filter(name=self.plugin_name, user_profile=self.user_profile).delete()
        )

    def test_get_returns_only_its_kind(self):
        """Test that get of each plugin kind returns only plugins of its class."""
        for kind in (
            SAMKinds.API_PLUGIN.value,
            SAMKinds.SQL_PLUGIN.value,
            SAMKinds.SKILL_PLUGIN.value,
            SAMKinds.WEBSEARCH_PLUGIN.value,
            SAMKinds.IMAGE_SEARCH_PLUGIN.value,
        ):
            with self.subTest(kind=kind):
                response, status = self.get_response(self.url(ApiV1CliReverseViews.get, kind))
                self.assertEqual(status, HTTPStatus.OK, response)
                items = TestGetAndDescribeEveryKind.items(response)
                self.assertNotIn(self.plugin_name, [item["name"] for item in items])
                self.assertEqual(len({item["pluginClass"] for item in items}), min(len(items), 1))
        response, status = self.get_response(self.url(ApiV1CliReverseViews.get, SAMKinds.STATIC_PLUGIN.value))
        self.assertEqual(status, HTTPStatus.OK, response)
        items = TestGetAndDescribeEveryKind.items(response)
        self.assertIn(self.plugin_name, [item["name"] for item in items])
        self.assertEqual({item["pluginClass"] for item in items}, {"static"})

    def test_describe_with_another_kind(self):
        """Test that describe of a static plugin as an ApiPlugin answers 404, not 500."""
        response, status = self.get_response(
            self.url(ApiV1CliReverseViews.describe, SAMKinds.API_PLUGIN.value, name=self.plugin_name)
        )
        self.assertEqual(status, HTTPStatus.NOT_FOUND, response)
        response, status = self.get_response(
            self.url(ApiV1CliReverseViews.describe, SAMKinds.STATIC_PLUGIN.value, name=self.plugin_name)
        )
        self.assertEqual(status, HTTPStatus.OK, response)
        self.assertEqual(response["data"]["metadata"]["name"], self.plugin_name)


class TestApplyResult(ApiV1CliTestBase):
    """Test that apply returns the resource's identity, and none of the broker's internals."""

    def test_apply_returns_only_the_resource(self):
        manifest = self.get_readonly_yaml_file(os.path.join(HERE, "data", "good-secret.yaml"))
        name = manifest["metadata"]["name"]  # type: ignore[index]
        self.addCleanup(lambda: Secret.objects.filter(name=name, user_profile=self.user_profile).delete())
        path = reverse(self.namespace + ApiV1CliReverseViews.apply)
        response, status = self.get_response(path, manifest=manifest)  # type: ignore[arg-type]
        self.assertEqual(status, HTTPStatus.OK, response)
        self.assertEqual(response["data"], {"apiVersion": "smarter.sh/v1", "kind": "Secret", "name": name})
        for leaked in ("api_token", "auth_header", "cache_key", "loader", "ip_address", "orm_instance"):
            self.assertNotIn(leaked, str(response))


class TestAnnotationSelectors(ApiV1CliTestBase):
    """Test annotations through the cli api: the Kubernetes map, legacy lists, and the get command's ?annotation= selector."""

    def url(self, view: str, kind: Optional[str] = None, **params) -> str:
        """The url of a cli view, with its query parameters.

        A list value repeats the parameter.
        """
        path = reverse(self.namespace + view, kwargs={SAMKeys.KIND.value: kind} if kind else None)
        return f"{path}?{urlencode(params, doseq=True)}" if params else path

    def apply(self, manifest: SmarterDictType) -> None:
        """Apply a Secret manifest, and delete the Secret after the test."""
        name = manifest["metadata"]["name"]
        self.addCleanup(lambda: Secret.objects.filter(name=name, user_profile=self.user_profile).delete())
        response, status = self.get_response(self.url(ApiV1CliReverseViews.apply), manifest=manifest)  # type: ignore[arg-type]
        self.assertEqual(status, HTTPStatus.OK, response)

    def names(self, kind: str, *selector: str) -> list[str]:
        """The names that get returns for a selector."""
        response, status = self.get_response(self.url(ApiV1CliReverseViews.get, kind, annotation=list(selector)))
        self.assertEqual(status, HTTPStatus.OK, response)
        return [item.get(SAMMetadataKeys.NAME.value, "") for item in TestGetAndDescribeEveryKind.items(response)]

    def describe(self, name: str) -> SmarterDictType:
        """The annotations that describe returns for a Secret."""
        response, status = self.get_response(self.url(ApiV1CliReverseViews.describe, SAMKinds.SECRET.value, name=name))
        self.assertEqual(status, HTTPStatus.OK, response)
        return response[SCLIResponseGet.DATA.value][SAMKeys.METADATA.value]["annotations"]

    def test_every_kind_applies_the_selector(self):
        """Test that get of every kind filters by annotation, so a key that nothing has returns nothing."""
        for kind in Brokers.all_brokers():
            with self.subTest(kind=kind):
                self.assertEqual(self.names(kind, "example.com/no-such-key"), [])
                everything, _ = self.get_response(self.url(ApiV1CliReverseViews.get, kind))
                count = everything[SCLIResponseGet.DATA.value][SAMKeys.METADATA.value]["count"]
                self.assertEqual(len(self.names(kind, "!example.com/no-such-key")), count)

    def test_invalid_selector_is_a_bad_request(self):
        """Test that an invalid selector answers 400."""
        response, status = self.get_response(
            self.url(ApiV1CliReverseViews.get, SAMKinds.SECRET.value, annotation="Bad Key=x")
        )
        self.assertEqual(status, HTTPStatus.BAD_REQUEST, response)

    def test_apply_select_describe(self):
        """Test that a map of annotations is applied, selected, described as strings, and replaced by the next apply."""
        manifest = self.get_readonly_yaml_file(os.path.join(HERE, "data", "annotated-secret.yaml"))
        self.apply(manifest)  # type: ignore[arg-type]
        self.assertEqual(
            self.describe("annotated_secret"),
            {
                "example.com/crm-account-id": "A-10042",
                "example.com/active": "true",
                "example.com/renewed": "2026-10-28",
                "smarter.sh/tests/purpose": "annotation selectors",
            },
        )
        secret = SAMKinds.SECRET.value
        self.assertEqual(self.names(secret, "example.com/crm-account-id=A-10042"), ["annotated_secret"])
        self.assertEqual(
            self.names(secret, "example.com/crm-account-id", "example.com/active=true"), ["annotated_secret"]
        )
        self.assertNotIn("annotated_secret", self.names(secret, "example.com/crm-account-id!=A-10042"))
        self.assertNotIn("annotated_secret", self.names(secret, "!example.com/active"))

        manifest["metadata"]["annotations"] = {"example.com/crm-account-id": "A-20000"}  # type: ignore[index]
        self.apply(manifest)  # type: ignore[arg-type]
        self.assertEqual(self.describe("annotated_secret"), {"example.com/crm-account-id": "A-20000"})
        self.assertEqual(self.names(secret, "example.com/crm-account-id=A-10042"), [])

    def test_apply_legacy_list(self):
        """Test that the list of one-key maps of older manifests still applies, and is described as a map."""
        manifest = self.get_readonly_yaml_file(os.path.join(HERE, "data", "good-secret.yaml"))
        self.apply(manifest)  # type: ignore[arg-type]
        annotations = self.describe(manifest["metadata"]["name"])  # type: ignore[index]
        self.assertEqual(annotations["smarter.sh/tests/owner"], "test bank")
        self.assertEqual(annotations["smarter.sh/tests/last-updated"], "2025-12-31")

    def test_invalid_annotations_are_a_bad_request(self):
        """Test that a manifest with an invalid key or a structured value answers 400."""
        manifest = self.get_readonly_yaml_file(os.path.join(HERE, "data", "annotated-secret.yaml"))
        for annotations in ({"Bad Key": "x"}, {"example.com/list": ["a", "b"]}):
            with self.subTest(annotations=annotations):
                manifest["metadata"]["annotations"] = annotations  # type: ignore[index]
                response, status = self.get_response(self.url(ApiV1CliReverseViews.apply), manifest=manifest)  # type: ignore[arg-type]
                self.assertEqual(status, HTTPStatus.BAD_REQUEST, response)
