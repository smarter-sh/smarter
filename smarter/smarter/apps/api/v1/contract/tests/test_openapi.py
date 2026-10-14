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
from django.urls import URLPattern, URLResolver
from django.urls.resolvers import RoutePattern
from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
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
    UNDOCUMENTED_URLCONFS,
    llmclient_paths,
    merge_paths,
    openapi_document,
    openapi_json,
)
from smarter.apps.api.v1.contract.sam import sam_models
from smarter.apps.api.v1.contract.tests.mixins import (
    REGENERATE,
    SKILL,
    OpenApiResponseMixin,
    committed_document,
)
from smarter.apps.guardrail.models import Guardrail, GuardrailEvent
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS
from smarter.apps.llmclient.models import (
    LLMClient,
    LLMClientAPIKey,
    LLMClientFunctions,
    LLMClientPlugin,
)
from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.mcpclient.caching import invalidate_cached_catalog
from smarter.apps.mcpclient.connection import MCPServerConnection
from smarter.apps.mcpclient.exceptions import SmarterMCPClientConnectionError
from smarter.apps.mcpclient.models import MCPClient
from smarter.apps.mcpclient.tests.base_classes import mock_mcp_server
from smarter.apps.secret.tests.factories import secret_factory
from smarter.common.const import PROJECT_ROOT
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.typing import SmarterDictType

CONTRACT = "smarter/smarter/apps/api/v1/contract/openapi.py"
"""The module that declares the document's routes, which failure messages point to."""

FIX_UNDOCUMENTED_ROUTE = (
    "To fix it, document the route: model its response in contract/models.py, build the view's response from "
    f"that model, add the operation to cli_paths() or the family's *_paths() function in {CONTRACT}, test a real "
    "response in TestOpenApiResponses, and run `make api-contract`. If the route must not be published, add it to "
    f"UNDOCUMENTED_ROUTES in {CONTRACT} with the reason instead. See 'Adding or changing a cli route' in {SKILL}."
)
"""What to do when a route of a documented family is not in the document."""

FIX_UNCOVERED_FAMILY = (
    f"To fix it, add the family's urlconf to DOCUMENTED_URLCONFS in {CONTRACT}, and list its routes in "
    "UNDOCUMENTED_ROUTES as NOT_YET_MODELED until they are documented. If the family must not be published, add "
    f"it to UNDOCUMENTED_URLCONFS with the reason instead. See 'Covering a new family of routes' in {SKILL}."
)
"""What to do when a family of routes under /api/v1 is not covered."""

FIX_REF = (
    "If openapi.json was edited or merged by hand, regenerate it: run `make api-contract`. If it is current, "
    f"{CONTRACT} builds a broken schema: a ref() names a model that is not in model_schemas() or cli_schemas(). "
    f"Add the model there, then run `make api-contract`. See {SKILL}."
)
"""What to do when the document's schemas or refs are broken."""

GUARDRAIL_MANIFEST = os.path.join(
    PROJECT_ROOT, "apps", "guardrail", "manifest", "brokers", "tests", "data", "guardrail.yaml"
)


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
        self.assertEqual(committed, openapi_json(), f"openapi.json is out of date. {REGENERATE}")

    def test_document_is_a_valid_model(self):
        document = OpenApiDocument.model_validate(committed_document())
        self.assertEqual(document.openapi, "3.1.0", f"openapi.json is not an OpenAPI 3.1 document. {REGENERATE}")
        self.assertEqual(
            document.model_dump(mode="json"),
            committed_document(),
            "openapi.json has content that contract/models.py doesn't model: it was edited by hand, or "
            f"OpenApiDocument changed. {REGENERATE}",
        )

    def test_refs_resolve(self):
        document = committed_document()
        schemas = document["components"]["schemas"]
        for ref in refs(document):
            with self.subTest(ref=ref):
                self.assertTrue(ref.startswith("#/components/schemas/"), f"{ref} is not a component schema. {FIX_REF}")
                self.assertIn(ref.rsplit("/", 1)[-1], schemas, f"{ref} names no schema. {FIX_REF}")

    def test_schemas_are_valid_json_schemas(self):
        for name, schema in committed_document()["components"]["schemas"].items():
            with self.subTest(schema=name):
                try:
                    Draft202012Validator.check_schema(schema)
                except SchemaError as error:
                    self.fail(f"{name} is not a valid JSON Schema: {error.message}. {FIX_REF}")

    def test_every_kind_is_a_manifest(self):
        schemas = committed_document()["components"]["schemas"]
        kinds = sorted(sam_models())
        self.assertEqual(schemas["SAMKind"]["enum"], kinds, f"SAMKind doesn't list the registered kinds. {REGENERATE}")
        mapping = schemas["SAMManifest"]["discriminator"]["mapping"]
        self.assertEqual(sorted(mapping), kinds, f"SAMManifest doesn't map the registered kinds. {REGENERATE}")
        for kind, ref in mapping.items():
            with self.subTest(kind=kind):
                self.assertEqual(
                    schemas[ref.rsplit("/", 1)[-1]]["properties"]["kind"]["const"],
                    kind,
                    f"{ref}'s kind is not the const {kind}. If openapi.json is current, cli_schemas() in "
                    f"{CONTRACT} no longer adds the const: restore it (see 'Design decisions' in {SKILL}). "
                    f"Otherwise: {REGENERATE}",
                )

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
                        path in paths or path in UNDOCUMENTED_ROUTES,
                        f"{path} is not in the OpenAPI document. {FIX_UNDOCUMENTED_ROUTE}",
                    )
        for path in UNDOCUMENTED_ROUTES:
            with self.subTest(undocumented=path):
                self.assertIn(
                    path,
                    routes,
                    f"{path} is listed in UNDOCUMENTED_ROUTES, but there is no such route. To fix it, remove it from "
                    f"UNDOCUMENTED_ROUTES in {CONTRACT}, or, if the route was renamed or its path parameter "
                    "changed, update the entry or PATH_PARAMETER_ALIASES to match.",
                )
                self.assertNotIn(
                    path,
                    paths,
                    f"{path} is documented, so it must not be in UNDOCUMENTED_ROUTES. To fix it, remove it from "
                    f"UNDOCUMENTED_ROUTES in {CONTRACT}.",
                )

    def test_every_family_is_covered(self):
        """A new family of routes under /api/v1 must be documented, or added to UNDOCUMENTED_URLCONFS."""
        families = {
            f"/{pattern.pattern}"
            for pattern in importlib.import_module("smarter.apps.api.v1.urls").urlpatterns
            if isinstance(pattern, URLResolver)
        }
        for family in families:
            with self.subTest(family=family):
                self.assertTrue(
                    family in DOCUMENTED_URLCONFS or family in UNDOCUMENTED_URLCONFS,
                    f"{family} is neither documented nor in UNDOCUMENTED_URLCONFS. {FIX_UNCOVERED_FAMILY}",
                )
        for family in UNDOCUMENTED_URLCONFS:
            with self.subTest(undocumented=family):
                self.assertIn(
                    family,
                    families,
                    f"{family} is in UNDOCUMENTED_URLCONFS, but smarter.apps.api.v1.urls mounts no such family. "
                    f"To fix it, remove it from UNDOCUMENTED_URLCONFS in {CONTRACT}, or correct its path.",
                )
                self.assertNotIn(
                    family,
                    DOCUMENTED_URLCONFS,
                    f"{family} is in both DOCUMENTED_URLCONFS and UNDOCUMENTED_URLCONFS. To fix it, remove it "
                    f"from UNDOCUMENTED_URLCONFS in {CONTRACT}.",
                )

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


class TestOpenApiResponses(OpenApiResponseMixin, ApiV1CliTestBase):
    """Test that the api's real responses are valid under the document's response schemas."""

    name = "test_openapi_guardrail"

    def setUp(self):
        super().setUp()
        with open(GUARDRAIL_MANIFEST, encoding="utf-8") as file:
            self.manifest = yaml.safe_load(file)
        self.manifest["metadata"]["name"] = self.name
        self.addCleanup(Guardrail.objects.filter(name=self.name).delete)

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

    def test_mcpclient_reads(self):
        """The MCPClients' reads, tools, reconnection and tool call, with an in-process MCP server, against the document."""
        with mock.patch("smarter.apps.mcpclient.receivers.refresh_mcpclient"):
            mcpclient = MCPClient.objects.create(
                name=self.name,
                user_profile=self.user_profile,
                transport="http",
                endpoint_url="https://mcp.example.com/mcp",
                auth_type="none",
            )
        self.addCleanup(MCPClient.objects.filter(pk=mcpclient.pk).delete)
        self.addCleanup(invalidate_cached_catalog, mcpclient)
        client = APIClient()
        headers = {"Authorization": f"Token {self.token_key}"}

        with mock_mcp_server():
            for template, path in {
                "/mcpclients/": "/mcpclients/",
                "/mcpclients/{id}/": f"/mcpclients/{mcpclient.hashed_id}/",
                "/mcpclients/{id}/tools/": f"/mcpclients/{mcpclient.pk}/tools/?refresh=true",
            }.items():
                with self.subTest(path=template):
                    status, body = self.rest_get(path)
                    self.assertEqual(status, HTTPStatus.OK, body)
                    self.assertValidResponse(template, "get", body)
            response = client.post(f"/api/v1/mcpclients/{mcpclient.pk}/refresh/", headers=headers)
            self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
            self.assertValidResponse("/mcpclients/{id}/refresh/", "post", response.json())
            response = client.post(
                f"/api/v1/mcpclients/{mcpclient.hashed_id}/tools/add_numbers/",
                {"a": 1, "b": 2},
                format="json",
                headers=headers,
            )
            self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
            self.assertValidResponse("/mcpclients/{id}/tools/{tool_name}/", "post", response.json())
            self.assertEqual(response.json()["content"], "3")

        # a failed connection is the error, beside the connection status.
        invalidate_cached_catalog(mcpclient)
        with mock.patch.object(MCPServerConnection, "discover", side_effect=SmarterMCPClientConnectionError("down")):
            status, body = self.rest_get(f"/mcpclients/{mcpclient.pk}/tools/?refresh=true")
        self.assertEqual(status, HTTPStatus.BAD_GATEWAY, body)
        self.assertValidResponse("/mcpclients/{id}/tools/", "get", body, status)
        self.assertEqual((body["detail"], body["status"]), ("down", "error"))

        status, body = self.rest_get("/mcpclients/999999999/")
        self.assertEqual(status, HTTPStatus.NOT_FOUND, body)
        self.assertValidResponse("/mcpclients/{id}/", "get", body, status)

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
