"""Test :mod:`smarter.apps.api.v1.contract.openapi`, and the ``export_api_contract`` command."""

import json
import os
import re
import tempfile
from http import HTTPStatus
from unittest import mock
from urllib.parse import urlencode

import yaml
from django.core.management import call_command
from django.urls import URLPattern
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.cli.urls import urlpatterns as cli_urlpatterns
from smarter.apps.api.v1.contract.const import (
    OPENAPI_PATH,
    SAM_EXAMPLE_SUFFIX,
    SAM_SCHEMA_SUFFIX,
)
from smarter.apps.api.v1.contract.models import OpenApiDocument
from smarter.apps.api.v1.contract.openapi import (
    UNDOCUMENTED_CLI_ROUTES,
    openapi_document,
    openapi_json,
)
from smarter.apps.api.v1.contract.sam import sam_models
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.llmclient.models import LLMClient
from smarter.common.const import PROJECT_ROOT
from smarter.lib.typing import SmarterDictType

GUARDRAIL_MANIFEST = os.path.join(
    PROJECT_ROOT, "apps", "guardrail", "manifest", "brokers", "tests", "data", "guardrail.yaml"
)
DOCUMENT_URI = "urn:smarter:openapi"


def committed_document() -> SmarterDictType:
    """The committed ``openapi.json``."""
    with open(OPENAPI_PATH, encoding="utf-8") as file:
        return json.load(file)


def refs(value) -> list[str]:
    """Every ``$ref`` in a JSON value."""
    if isinstance(value, dict):
        own = [value["$ref"]] if "$ref" in value else []
        return own + [ref for item in value.values() for ref in refs(item)]
    if isinstance(value, list):
        return [ref for item in value for ref in refs(item)]
    return []


class TestOpenApiDocument(ApiV1CliTestBase):
    """Test the cli api's OpenAPI document."""

    def test_committed_document_is_up_to_date(self):
        """Openapi.json must be regenerated when a SAM model, a contract model or the cli api changes."""
        with open(OPENAPI_PATH, encoding="utf-8") as file:
            committed = file.read()
        self.assertEqual(committed, openapi_json(), "openapi.json is out of date. Run `manage.py export_api_contract`.")

    def test_document_is_a_valid_model(self):
        document = OpenApiDocument.model_validate(committed_document())
        self.assertEqual(document.openapi, "3.1.0")
        self.assertEqual(document.model_dump(mode="json"), committed_document())

    def test_refs_resolve(self):
        document = committed_document()
        schemas = document["components"]["schemas"]
        for ref in refs(document):
            with self.subTest(ref=ref):
                self.assertTrue(ref.startswith("#/components/schemas/"), ref)
                self.assertIn(ref.rsplit("/", 1)[-1], schemas)

    def test_schemas_are_valid_json_schemas(self):
        for name, schema in committed_document()["components"]["schemas"].items():
            with self.subTest(schema=name):
                Draft202012Validator.check_schema(schema)

    def test_every_kind_is_a_manifest(self):
        schemas = committed_document()["components"]["schemas"]
        kinds = sorted(sam_models())
        self.assertEqual(schemas["SAMKind"]["enum"], kinds)
        mapping = schemas["SAMManifest"]["discriminator"]["mapping"]
        self.assertEqual(sorted(mapping), kinds)
        for kind, ref in mapping.items():
            with self.subTest(kind=kind):
                self.assertEqual(schemas[ref.rsplit("/", 1)[-1]]["properties"]["kind"]["const"], kind)

    def test_every_cli_route_is_documented(self):
        """A new cli route must be added to the document, or to UNDOCUMENTED_CLI_ROUTES."""
        paths = openapi_document().paths
        for pattern in cli_urlpatterns:
            if not isinstance(pattern, URLPattern) or not pattern.name:
                continue  # e.g. the legacy schema/ redirect
            path = "/cli/" + re.sub(r"<(?:\w+:)?(\w+)>", r"{\1}", str(pattern.pattern))
            with self.subTest(route=pattern.name):
                self.assertTrue(
                    path in paths or path in UNDOCUMENTED_CLI_ROUTES,
                    f"{path} is not in the OpenAPI document.",
                )

    def test_public_operations(self):
        paths = openapi_document().paths
        public = sorted(path for path, item in paths.items() if item.post and item.post.security == [])
        self.assertEqual(public, ["/cli/example-manifest/{kind}/", "/cli/json-schema/{kind}/"])

    def test_export_command(self):
        with tempfile.TemporaryDirectory() as directory:
            openapi = os.path.join(directory, "openapi.json")
            call_command("export_api_contract", sam_dir=directory, openapi=openapi)
            with open(openapi, encoding="utf-8") as file:
                self.assertEqual(file.read(), openapi_json())
            schemas = [name for name in os.listdir(directory) if name.endswith(SAM_SCHEMA_SUFFIX)]
            self.assertEqual(len(schemas), len(sam_models()))
            examples = [name for name in os.listdir(directory) if name.endswith(SAM_EXAMPLE_SUFFIX)]
            self.assertEqual(len(examples), len(sam_models()))


class TestOpenApiResponses(ApiV1CliTestBase):
    """Test that the cli's real responses are valid under the document's response schemas."""

    name = "test_openapi_guardrail"

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        registry = Registry().with_resource(
            DOCUMENT_URI, Resource.from_contents(committed_document(), default_specification=DRAFT202012)
        )
        cls.registry = registry

    def setUp(self):
        super().setUp()
        with open(GUARDRAIL_MANIFEST, encoding="utf-8") as file:
            self.manifest = yaml.safe_load(file)
        self.manifest["metadata"]["name"] = self.name
        self.addCleanup(Guardrail.objects.filter(name=self.name).delete)

    def assertValid(self, schema_name: str, body: SmarterDictType):
        """Assert that a response body is valid under one of the document's schemas."""
        validator = Draft202012Validator(
            {"$ref": f"{DOCUMENT_URI}#/components/schemas/{schema_name}"}, registry=self.registry
        )
        errors = [f"{list(error.absolute_path)}: {error.message[:300]}" for error in validator.iter_errors(body)]
        self.assertEqual(errors, [], f"{schema_name}: {body}")

    def post(self, path: str, data=None) -> SmarterDictType:
        """POST to the cli, and return the response's body, which must be a success."""
        response, status = self.get_response(path=f"/api/v1/cli/{path}", data=data)
        self.assertEqual(status, HTTPStatus.OK, response)
        return response

    def test_manifest_lifecycle(self):
        """Apply, get, describe and delete, the commands that the SDKs call most."""
        self.assertValid("CliApiApplyResponse", self.post("apply/", self.manifest))
        self.assertValid("CliApiGetResponse", self.post("get/Guardrail/"))
        self.assertValid("CliApiManifestResponse", self.post(f"describe/Guardrail/?name={self.name}"))
        self.assertValid("CliApiMessageResponse", self.post(f"delete/Guardrail/?name={self.name}"))

    def test_validate(self):
        self.assertValid("CliApiValidateResponse", self.post("validate/", self.manifest))
        invalid = {"apiVersion": "smarter.sh/v1", "kind": "Guardrail"}
        body = self.post("validate/", invalid)
        self.assertValid("CliApiValidateResponse", body)
        self.assertFalse(body["data"]["valid"])

    def test_error(self):
        response, status = self.get_response(path="/api/v1/cli/describe/Guardrail/?name=does_not_exist")
        self.assertEqual(status, HTTPStatus.NOT_FOUND, response)
        self.assertValid("CliApiErrorResponse", response)

    def test_example_manifests_and_json_schemas(self):
        for kind in sam_models():
            with self.subTest(kind=kind):
                self.assertValid("CliApiManifestResponse", self.post(f"example-manifest/{kind}/"))
                self.assertValid("CliApiJsonSchemaResponse", self.post(f"json-schema/{kind}/"))

    def test_platform(self):
        """Status, version, whoami and resources, without the cloud infrastructure or GitHub."""
        with mock.patch(
            "smarter.apps.api.v1.cli.views.nonbrokered.status.ApiV1CliStatusApiView.get_kubernetes_info",
            return_value={"status": "ACTIVE", "version": "1.36"},
        ):
            self.assertValid("CliApiStatusResponse", self.post("status/"))
        with mock.patch(
            "smarter.apps.api.v1.cli.views.nonbrokered.version.ApiV1CliVersionApiView.cli_version",
            return_value="0.4.0",
        ):
            self.assertValid("CliApiVersionResponse", self.post("version/"))
        self.assertValid("CliApiWhoamiResponse", self.post("whoami/"))
        body = self.post("resources/")
        self.assertValid("CliApiResourcesResponse", body)
        self.assertEqual(body["metadata"]["command"], "resources")

    def test_chat(self):
        """Prompt/config and prompt, with a real LLM call."""
        llmclient = LLMClient.objects.create(
            name=self.name,
            user_profile=self.user_profile,
            description="Test LLMClient",
            version="1.0.0",
            app_name="Smarter",
            app_assistant="Smarty Pants",
            app_welcome_message="Welcome to Smarter!",
        )
        self.addCleanup(llmclient.delete)
        query = urlencode({"uid": f"{self.name}_uid", "new_session": "true"})
        self.assertValid("PromptChatApiConfigResponse", self.post(f"prompt/config/{self.name}/?{query}"))
        body = self.post(f"prompt/{self.name}/?{query}", {"prompt": "Say hello in two words."})
        self.assertValid("CliApiPromptResponse", body)
