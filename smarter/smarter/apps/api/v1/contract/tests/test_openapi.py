"""Test :mod:`smarter.apps.api.v1.contract.openapi`, and the ``export_api_contract`` command."""

import asyncio
import copy
import importlib
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
from django.urls.resolvers import RoutePattern
from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012
from rest_framework.test import APIClient

from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.contract.const import (
    OPENAPI_PATH,
    SAM_EXAMPLE_SUFFIX,
    SAM_SCHEMA_SUFFIX,
)
from smarter.apps.api.v1.contract.models import OpenApiDocument
from smarter.apps.api.v1.contract.openapi import (
    DOCUMENTED_URLCONFS,
    PATH_PARAMETER_ALIASES,
    UNDOCUMENTED_ROUTES,
    llmclient_paths,
    merge_paths,
    openapi_document,
    openapi_json,
)
from smarter.apps.api.v1.contract.sam import sam_models
from smarter.apps.guardrail.models import Guardrail, GuardrailEvent
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientFunctions,
    LLMClientPlugin,
)
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.secret.tests.factories import secret_factory
from smarter.common.const import PROJECT_ROOT
from smarter.lib.drf.models import SmarterAuthToken
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
    """Test the Smarter api's OpenAPI document."""

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

    def test_every_route_is_documented(self):
        """A new route of a documented family must be added to the document, or to UNDOCUMENTED_ROUTES."""
        paths = openapi_document().paths
        routes = set()
        for prefix, urlconf in DOCUMENTED_URLCONFS.items():
            for pattern in importlib.import_module(urlconf).urlpatterns:
                if not isinstance(pattern, URLPattern) or not isinstance(pattern.pattern, RoutePattern):
                    continue  # e.g. the cli's legacy schema/ redirect, a re_path
                path = prefix + re.sub(
                    r"<(?:\w+:)?(\w+)>",
                    lambda match: "{" + PATH_PARAMETER_ALIASES.get(match.group(1), match.group(1)) + "}",
                    str(pattern.pattern),
                )
                routes.add(path)
                with self.subTest(route=path):
                    self.assertTrue(
                        path in paths or path in UNDOCUMENTED_ROUTES, f"{path} is not in the OpenAPI document."
                    )
        for path in UNDOCUMENTED_ROUTES:
            with self.subTest(undocumented=path):
                self.assertIn(path, routes, f"{path} is listed as undocumented, but there is no such route.")
                self.assertNotIn(path, paths, f"{path} is documented, so remove it from UNDOCUMENTED_ROUTES.")

    def test_merge_paths(self):
        """Families merge into one document, and an operation that two families define is refused."""
        paths = merge_paths(llmclient_paths(), {"/other/": llmclient_paths()["/llm-clients/"]})
        self.assertIn("/other/", paths)
        with self.assertRaises(ValueError):
            merge_paths(llmclient_paths(), llmclient_paths())

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

    def assertValidResponse(self, path: str, method: str, body, status: int = 200):
        """Assert that a response body is valid under the schema that the document gives its operation and status."""
        operation = getattr(openapi_document().paths[path], method)
        response = operation.responses.get(str(status)) or operation.responses["default"]
        schema = response.content["application/json"].schema_
        errors = [
            f"{list(error.absolute_path)}: {error.message[:300]}"
            for error in Draft202012Validator(
                json.loads(json.dumps(schema).replace('"#/components/', f'"{DOCUMENT_URI}#/components/')),
                registry=self.registry,
            ).iter_errors(body)
        ]
        self.assertEqual(errors, [], f"{method.upper()} {path} {status}: {str(body)[:500]}")

    def rest_get(self, path: str) -> tuple[int, object]:
        """GET a REST api path, with the api key of the test's superuser."""
        response = APIClient().get(f"/api/v1{path}", headers={"Authorization": f"Token {self.token_key}"})
        return response.status_code, response.json()

    def test_llmclient_reads(self):
        """Every read of the LLMClients' REST api, its 404 and its 403, against the document."""
        llmclient = LLMClient.objects.create(name=self.name, user_profile=self.user_profile)
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        function = LLMClientFunctions.objects.create(llmclient=llmclient, name="calculator")
        plugin_meta = PluginMeta.objects.create(name=self.name, user_profile=self.user_profile, plugin_class="static")
        self.addCleanup(PluginMeta.objects.filter(pk=plugin_meta.pk).delete)
        plugin = LLMClientPlugin.objects.create(llmclient=llmclient, plugin_meta=plugin_meta)
        token, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user_profile=self.user_profile, name=self.name, user=self.admin_user, description=self.name
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=token.pk).delete)
        api_key = LLMClientAPIKey.objects.create(llmclient=llmclient, api_key=token)

        reads = {
            "/llm-clients/": "/llm-clients/",
            "/llm-clients/{id}/": f"/llm-clients/{llmclient.hashed_id}/",
            "/llm-clients/{id}/plugins/": f"/llm-clients/{llmclient.pk}/plugins/",
            "/llm-clients/{id}/plugins/{plugin_id}/": f"/llm-clients/{llmclient.pk}/plugins/{plugin.pk}/",
            "/llm-clients/{id}/apikeys/": f"/llm-clients/{llmclient.pk}/apikeys/",
            "/llm-clients/{id}/apikeys/{apikey_id}/": f"/llm-clients/{llmclient.pk}/apikeys/{api_key.pk}/",
            "/llm-clients/{id}/customdomains": f"/llm-clients/{llmclient.pk}/customdomains",
            "/llm-clients/{id}/functions": f"/llm-clients/{llmclient.pk}/functions",
            "/llm-clients/{id}/functions/{function_id}": f"/llm-clients/{llmclient.pk}/functions/{function.pk}",
        }
        for template, path in reads.items():
            with self.subTest(path=template):
                status, body = self.rest_get(path)
                self.assertEqual(status, HTTPStatus.OK, body)
                self.assertValidResponse(template, "get", body)
                # a custom domain can't be created here: saving one reaches DNS.
                if isinstance(body, list) and template != "/llm-clients/{id}/customdomains":
                    self.assertTrue(body, f"{template} returned no rows to validate.")
        status, body = self.rest_get(f"/llm-clients/{llmclient.pk}/")
        self.assertEqual(body["functions"][0]["name"], "calculator")
        # an api key is its token's public key_id, never the token's digest, its primary key.
        self.assertEqual(body["apiKeys"][0]["apiKey"], str(token.key_id))
        status, body = self.rest_get(f"/llm-clients/{llmclient.pk}/apikeys/")
        self.assertEqual([item["apiKey"] for item in body], [str(token.key_id)])
        self.assertNotIn(token.digest, json.dumps(body))

        for path in ("/llm-clients/999999999/", "/llm-clients/rNotAHashedId/"):
            with self.subTest(not_found=path):
                status, body = self.rest_get(path)
                self.assertEqual(status, HTTPStatus.NOT_FOUND, body)
                self.assertValidResponse("/llm-clients/{id}/", "get", body, status)

        # a user who is not a superuser. Only staff may have an api key, so the user is authenticated directly.
        client = APIClient()
        client.force_authenticate(user=self.non_admin_user)
        response = client.get("/api/v1/llm-clients/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.content)
        self.assertValidResponse("/llm-clients/", "get", response.json(), response.status_code)

    def test_guardrail_reads(self):
        """The Guardrails' reads, their dry run, their events, and their errors, against the document."""
        guardrail = Guardrail.objects.create(
            name=self.name, user_profile=self.user_profile, **copy.deepcopy(GUARDRAIL_DEFAULTS)
        )
        self.addCleanup(Guardrail.objects.filter(pk=guardrail.pk).delete)
        event = GuardrailEvent.objects.create(
            guardrail=guardrail,
            guardrail_name=guardrail.name,
            stage="input",
            category="custom",
            strategy="keyword",
            action="block",
            mode="enforce",
            disposition="blocked",
            severity=3,
        )
        self.addCleanup(GuardrailEvent.objects.filter(pk=event.pk).delete)
        for template, path in {
            "/guardrails/": "/guardrails/",
            "/guardrails/{id}/": f"/guardrails/{guardrail.hashed_id}/",
            "/guardrails/{id}/events/": f"/guardrails/{guardrail.pk}/events/?disposition=blocked",
        }.items():
            with self.subTest(path=template):
                status, body = self.rest_get(path)
                self.assertEqual(status, HTTPStatus.OK, body)
                self.assertValidResponse(template, "get", body)
        self.assertEqual(self.rest_get(f"/guardrails/{guardrail.pk}/events/")[1]["events"][0]["id"], event.pk)

        client = APIClient()
        headers = {"Authorization": f"Token {self.token_key}"}
        path = f"/api/v1/guardrails/{guardrail.hashed_id}/evaluate/"
        response = client.post(path, {"text": "this is forbidden", "stage": "input"}, format="json", headers=headers)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
        self.assertValidResponse("/guardrails/{id}/evaluate/", "post", response.json())
        self.assertTrue(response.json()["triggered"])
        for invalid in ({}, {"text": "x", "stage": "sideways"}):
            with self.subTest(invalid=invalid):
                response = client.post(path, invalid, format="json", headers=headers)
                self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST, response.content)
                self.assertValidResponse("/guardrails/{id}/evaluate/", "post", response.json(), response.status_code)

        status, body = self.rest_get("/guardrails/999999999/")
        self.assertEqual(status, HTTPStatus.NOT_FOUND, body)
        self.assertValidResponse("/guardrails/{id}/", "get", body, status)

    def test_secret_reads(self):
        """The Secrets' reads, without their values, and their errors, against the document."""
        value = "not-a-real-secret-value"
        secret = secret_factory(self.user_profile, f"{self.name}_secret", "A test secret.", value)
        self.addCleanup(secret.delete)
        for template, path in {"/secrets/": "/secrets/", "/secrets/{id}/": f"/secrets/{secret.pk}/"}.items():
            with self.subTest(path=template):
                status, body = self.rest_get(path)
                self.assertEqual(status, HTTPStatus.OK, body)
                self.assertValidResponse(template, "get", body)
                self.assertNotIn(value, json.dumps(body))
        status, body = self.rest_get("/secrets/999999999/")
        self.assertEqual(status, HTTPStatus.NOT_FOUND, body)
        self.assertValidResponse("/secrets/{id}/", "get", body, status)
        client = APIClient()
        client.force_authenticate(user=self.non_admin_user)
        response = client.get("/api/v1/secrets/")
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.content)
        self.assertValidResponse("/secrets/", "get", response.json(), response.status_code)

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

    def chat_post(self, path: str, body: SmarterDictType, **headers) -> tuple[int, object]:
        """POST JSON to the chat api, as a client of version 2 of the chat contract."""
        client = APIClient()
        response = client.post(
            f"/api/v1/{path}",
            data=body,
            format="json",
            headers={
                "Authorization": f"Token {self.token_key}",
                "X-Smarter-Capabilities": "chat-contract-v2",
                **headers,
            },
        )
        return response.status_code, response

    @staticmethod
    def sse_events(response) -> list[tuple[str, SmarterDictType]]:
        """The (event, data) of each event of a streaming response, without its retry and keepalive frames."""

        async def collect():
            return [chunk.decode() if isinstance(chunk, bytes) else chunk async for chunk in response.streaming_content]

        events = []
        for frame in "".join(asyncio.run(collect())).split("\n\n"):
            lines = dict(line.split(": ", 1) for line in frame.splitlines() if line.startswith(("event: ", "data: ")))
            if "event" in lines:
                events.append((lines["event"], json.loads(lines["data"])))
        return events

    def test_chat_api(self):
        """The chat api's configuration, its prompt as JSON and as a stream, and its error, with real LLM calls."""
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

        status, response = self.chat_post(f"llm-clients/{llmclient.id}/config/", {"session_key": None})
        self.assertEqual(status, HTTPStatus.OK, response.content)
        config = response.json()
        self.assertValid("PromptChatApiConfigResponse", config)
        session_key = config["data"]["session_key"]

        messages = [{"role": "user", "content": "Say hello in two words."}]
        status, response = self.chat_post(
            f"llm-clients/{llmclient.hashed_id}/prompt/", {"session_key": session_key, "messages": messages}
        )
        self.assertEqual(status, HTTPStatus.OK, response.content)
        self.assertValid("PromptChatApiPromptResponse", response.json())

        status, response = self.chat_post(
            f"llm-clients/{llmclient.id}/prompt/",
            {"session_key": session_key, "messages": messages},
            Accept="text/event-stream, application/json",
        )
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        events = self.sse_events(response)
        self.assertEqual(events[-1][0], "result")
        self.assertGreater(len(events), 1)
        stream = OpenApiDocument.model_validate(committed_document()).paths["/llm-clients/{id}/prompt/"]
        schemas = stream.post.responses["200"].content["text/event-stream"].x_smarter_events
        for event, data in events:
            with self.subTest(event=event):
                self.assertIn(event, schemas)
                self.assertValid(schemas[event]["$ref"].rsplit("/", 1)[-1], data)
        self.assertValid("PromptChatApiPromptResponse", events[-1][1]["response"])

        status, response = self.chat_post("llm-clients/999999999/config/", {})
        self.assertEqual(status, HTTPStatus.NOT_FOUND, response.content)
        self.assertValid("PromptChatApiErrorResponse", response.json())

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
