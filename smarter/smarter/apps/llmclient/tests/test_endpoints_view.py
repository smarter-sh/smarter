"""Test :mod:`smarter.apps.llmclient.views.endpoints`, the page that a browser sees at a deployed LLMClient's endpoints."""

import json
import re
import shlex
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, patch

import yaml
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, override_settings
from django.urls import resolve

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.manifest.brokers.llmclient import SAMLLMClientBrokerError
from smarter.apps.llmclient.manifest.models.llmclient.model import SAMLLMClient
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmclient.templatetags.react_llmclient_deployment import (
    DEPLOYMENT_DATA_ID,
    DEPLOYMENT_ROOT_ID,
)
from smarter.apps.llmclient.views.deployment_contract import LLMClientDeploymentPage
from smarter.apps.llmclient.views.endpoints import (
    EMBED_SCRIPT_URL,
    EXAMPLE_PROMPT,
    EXAMPLE_RESPONSE_CONTENT,
    SESSION_KEY_PLACEHOLDER,
    SWITCH_COMMAND,
    api_keys_url,
    browser_friendly,
    cached_manifest_yaml,
    create_api_key_command,
    curl_command,
    deployment_page,
    embed_html,
    example_prompt,
    example_response,
    llmclient_manifest,
    manifest_yaml,
    react_snippet,
)
from smarter.apps.prompt.contract.models import (
    PromptChatApiPromptRequest,
    PromptChatApiPromptResponse,
)
from smarter.lib.django.templatetags.smarter_react_contract import ReactAppAssets

MODULE = "smarter.apps.llmclient.views.endpoints"
SWITCH = f"{MODULE}.waffle.switch_is_active"
LLMCLIENTS_URLCONF = "smarter.urls.llmclients"
CONSOLE_URLCONF = "smarter.urls.console"
SYSTEM_ROLE = "You are a helpful assistant.\nAnswer in <b>one</b> sentence."
FIRST_EXAMPLE_PROMPT = "What courses are there?"


def page_data(html: str) -> dict:
    """The deployment page's data, from its json_script, validated by its contract."""
    match = re.search(rf'<script id="{DEPLOYMENT_DATA_ID}" type="application/json">(.*?)</script>', html, re.S)
    assert match, "the page has no data"
    data = json.loads(match[1])
    LLMClientDeploymentPage.model_validate(data)
    return data


class TestLLMClientEndpointsView(TestAccountMixin):
    """Test that a GET of a deployed LLMClient's endpoints is a page about it, and a POST is its api."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_endpoints_{self.hash_suffix}",
            user_profile=self.user_profile,
            description="Answers questions about <courses>.",
            default_system_role=SYSTEM_ROLE,
            app_example_prompts=["What courses are there?"],
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=True)
        self.llmclient.refresh_from_db()
        self.host = f"endpoints.{self.account.account_number}.api.example.com"
        self.factory = RequestFactory()

    def request(self, path: str = "/", method: str = "get"):
        request = getattr(self.factory, method)(path, HTTP_HOST=self.host)
        request.user = AnonymousUser()
        return request

    def get(self, path: str = "/", llmclient=None, method: str = "get", urlconf=LLMCLIENTS_URLCONF) -> HttpResponse:
        """GET the path from a urlconf, with the host resolved to ``llmclient``."""
        view = resolve(path, urlconf=urlconf).func
        with (
            override_settings(ALLOWED_HOSTS=["*"]),
            patch(SWITCH, return_value=True),
            patch(f"{MODULE}.get_cached_llmclient_by_request", return_value=llmclient),
        ):
            return view(self.request(path, method))

    def test_every_endpoint_serves_the_page(self):
        base_url = self.llmclient.url.rstrip("/")
        for path in ("/", "/config/", "/prompt/"):
            with self.subTest(path=path):
                response = self.get(path, self.llmclient)
                self.assertEqual(response.status_code, HTTPStatus.OK)
                self.assertTrue(response["Content-Type"].startswith("text/html"))
                html = response.content.decode()
                self.assertIn(f'id="{DEPLOYMENT_ROOT_ID}"', html)
                self.assertIn(f'smarter-deployment-data-id="{DEPLOYMENT_DATA_ID}"', html)
                # the React app's text is translated with the djangojs catalog, from the LLMClient's own host.
                self.assertIn('<script src="/jsi18n/"></script>', html)
                page = page_data(html)
                self.assertEqual(page["mode"], "public")
                self.assertTrue(page["deployed"])
                self.assertFalse(page["authenticated"])
                # anyone can open the page: it names no owner, and has no api keys.
                self.assertIsNone(page["ownership"])
                self.assertIsNone(page["apiKeys"])
                self.assertNotIn(self.admin_user.username, html)
                llmclient = page["llmclient"]
                self.assertEqual(llmclient["name"], self.llmclient.name)
                self.assertEqual(llmclient["url"], base_url)
                self.assertEqual(llmclient["workbenchUrl"], self.llmclient.workbench_url)
                self.assertEqual(llmclient["examplePrompts"], [FIRST_EXAMPLE_PROMPT])
                snippets = page["snippets"]
                self.assertIn(f"{base_url}/config/", snippets["configCommand"])
                # the /prompt/ command sends the LLMClient's first example prompt.
                self.assertIn(f"{base_url}/prompt/", snippets["promptCommand"])
                self.assertIn(f'"content":"{FIRST_EXAMPLE_PROMPT}"', snippets["promptCommand"])
                self.assertNotIn(EXAMPLE_PROMPT, snippets["promptCommand"])
                # a public LLMClient's commands send no api key.
                self.assertNotIn("Authorization", snippets["promptCommand"])
                # the chat session's commands carry its key: a prompt, and the config request that continues it.
                self.assertIn(f"{base_url}/prompt/", snippets["sessionPromptCommand"])
                self.assertIn(f'"session_key":"{SESSION_KEY_PLACEHOLDER}"', snippets["sessionPromptCommand"])
                self.assertIn(f'"content":"{FIRST_EXAMPLE_PROMPT}"', snippets["sessionPromptCommand"])
                self.assertIn(f"{base_url}/config/", snippets["sessionConfigCommand"])
                self.assertIn(f'\'{{"session_key":"{SESSION_KEY_PLACEHOLDER}"}}\'', snippets["sessionConfigCommand"])
                self.assertIn(EMBED_SCRIPT_URL, snippets["embedHtml"])
                self.assertIn(f'data-chatbot="{base_url}/"', snippets["embedHtml"])
                self.assertIn('data-api-key="<YOUR-API-KEY>"', snippets["embedHtmlWithApiKey"])
                self.assertIn("allowedOrigins", snippets["allowedOriginsYaml"])
                self.assertIn(f"--account_number {self.account.account_number}", snippets["createApiKeyCommand"])
                self.assertEqual(snippets["apiKeyYaml"], "spec:\n  apiKey: <API-KEY-NAME>")
                self.assertEqual(snippets["switchCommand"], SWITCH_COMMAND)
                self.assertEqual(page["links"]["apiKeysUrl"], api_keys_url())
                self.assertTrue(page["links"]["logoUrl"].endswith("smarter-crop.png"))
                # the manifest, with its system role, is in the data as text: json_script escapes its html.
                self.assertIn("Answer in <b>one</b> sentence.", page["manifestYaml"])
                self.assertNotIn("<b>one</b>", html)
                self.assertNotIn("<courses>", html)

    def test_the_page_is_the_react_app(self):
        manager = "smarter.apps.llmclient.templatetags.react_llmclient_deployment.templatetag_manager"
        assets = ReactAppAssets(css=["assets/index.css"], js=["assets/index.js"])
        with patch(f"{manager}.reactapp_build_assets", assets):
            html = self.get("/", self.llmclient).content.decode()
        self.assertIn("/static/react/%40smarter/llmclient-deployment/assets/index.css", html)
        self.assertIn('type="module" src="/static/react/%40smarter/llmclient-deployment/assets/index.js"', html)

    def test_the_manifest_keeps_its_indentation(self):
        page = page_data(self.get("/", self.llmclient).content.decode())
        self.assertIn("\n  name: ", page["manifestYaml"])
        self.assertIn("\n    prompt:", page["manifestYaml"])

    def test_custom_domain_endpoints_serve_the_page(self):
        for path in ("/config/", "/prompt/"):
            with self.subTest(path=path):
                response = self.get(path, self.llmclient, urlconf=CONSOLE_URLCONF)
                self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_head_serves_the_page(self):
        response = self.get("/prompt/", self.llmclient, method="head")
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_an_llmclient_with_api_keys(self):
        with patch.object(LLMClient, "is_authentication_required", new_callable=PropertyMock, return_value=True):
            response = self.get("/", self.llmclient)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        page = page_data(response.content.decode())
        self.assertTrue(page["authenticated"])
        self.assertIn("Authorization: Token <YOUR-API-KEY>", page["snippets"]["promptCommand"])
        self.assertIn("Authorization: Token <YOUR-API-KEY>", page["snippets"]["configCommand"])
        self.assertIn("Authorization: Token <YOUR-API-KEY>", page["snippets"]["sessionConfigCommand"])
        self.assertIn("Authorization: Token <YOUR-API-KEY>", page["snippets"]["sessionPromptCommand"])
        self.assertIn('data-api-key="<YOUR-API-KEY>"', page["snippets"]["embedHtml"])
        self.assertIn("apiKey={import.meta.env.VITE_SMARTER_API_KEY}", page["snippets"]["reactSnippet"])

    def test_a_host_without_an_llmclient(self):
        for urlconf in (LLMCLIENTS_URLCONF, CONSOLE_URLCONF):
            with self.subTest(urlconf=urlconf):
                response = self.get("/config/", None, urlconf=urlconf)
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_an_llmclient_that_is_not_deployed(self):
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=False)
        self.llmclient.refresh_from_db()
        response = self.get("/prompt/", self.llmclient)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_get_goes_to_the_api_view_while_the_switch_is_inactive(self):
        api_view = MagicMock(return_value=HttpResponse("api", status=HTTPStatus.METHOD_NOT_ALLOWED))
        request = self.request("/config/")
        with patch(SWITCH, return_value=False):
            response = browser_friendly(api_view)(request)
        self.assertEqual(response.status_code, HTTPStatus.METHOD_NOT_ALLOWED)
        api_view.assert_called_once_with(request)

    def test_the_page_without_its_manifest(self):
        with patch(f"{MODULE}.cached_manifest_yaml", side_effect=SAMLLMClientBrokerError("no", thing="LLMClient")):
            response = self.get("/", self.llmclient)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        page = page_data(response.content.decode())
        self.assertIsNone(page["manifestYaml"])
        self.assertEqual(page["llmclient"]["examplePrompts"], [FIRST_EXAMPLE_PROMPT])

    def test_post_goes_to_the_api_view(self):
        api_view = MagicMock(return_value=HttpResponse("api"))
        api_view.csrf_exempt = True
        view = browser_friendly(api_view)
        self.assertTrue(view.csrf_exempt)
        request = self.request("/prompt/", "post")
        response = view(request, name="x")
        self.assertEqual(response.content, b"api")
        api_view.assert_called_once_with(request, name="x")

    def test_get_does_not_reach_the_api_view(self):
        api_view = MagicMock(return_value=HttpResponse("api"))
        with (
            patch(SWITCH, return_value=True),
            patch(f"{MODULE}.get_cached_llmclient_by_request", return_value=self.llmclient),
        ):
            response = browser_friendly(api_view)(self.request("/config/"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        api_view.assert_not_called()

    def test_the_urlconfs_keep_the_api_views_csrf_exempt(self):
        for urlconf, paths in (
            (LLMCLIENTS_URLCONF, ("/", "/config/", "/prompt/")),
            (CONSOLE_URLCONF, ("/config/", "/prompt/")),
        ):
            for path in paths:
                with self.subTest(urlconf=urlconf, path=path):
                    self.assertTrue(getattr(resolve(path, urlconf=urlconf).func, "csrf_exempt", False))

    def test_the_manifest(self):
        manifest = llmclient_manifest(self.llmclient)
        self.assertIsInstance(manifest, SAMLLMClient)
        text = manifest_yaml(manifest)
        data = yaml.safe_load(text)
        self.assertEqual(data["kind"], "LLMClient")
        self.assertEqual(data["metadata"]["name"], self.llmclient.name)
        prompt = data["spec"]["config"]["prompt"]
        self.assertEqual(prompt["defaultSystemRole"], SYSTEM_ROLE)
        self.assertEqual(prompt["appExamplePrompts"], ["What courses are there?"])
        self.assertTrue(prompt["deployed"])
        self.assertEqual(data["status"]["accountNumber"], self.account.account_number)
        # without the owner's username, and without empty values.
        self.assertNotIn("username", data["status"])
        self.assertNotIn(": null", text)

    def test_a_manifest_that_cannot_be_built(self):
        with patch(
            "smarter.apps.llmclient.manifest.brokers.llmclient.SAMLLMClientBroker.django_orm_to_manifest_dict",
            return_value=None,
        ):
            with self.assertRaises(SAMLLMClientBrokerError):
                llmclient_manifest(self.llmclient)

    def test_cached_manifest_yaml(self):
        updated_at = self.llmclient.updated_at.isoformat()
        with patch(f"{MODULE}.llmclient_manifest", wraps=llmclient_manifest) as build:
            first = cached_manifest_yaml(self.llmclient.pk, updated_at)
            second = cached_manifest_yaml(self.llmclient.pk, updated_at)
        self.assertEqual(first, second)
        self.assertEqual(build.call_count, 1)
        cached_manifest_yaml.invalidate(self.llmclient.pk, updated_at)

    def test_manifest_yaml_writes_multi_line_strings_as_blocks(self):
        text = manifest_yaml(llmclient_manifest(self.llmclient))
        self.assertIn("defaultSystemRole: |", text)
        self.assertIn("\n        Answer in <b>one</b> sentence.", text)

    def test_the_deployment_page_of_an_llmclient_that_is_not_deployed(self):
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=False)
        self.llmclient.refresh_from_db()
        page = deployment_page(self.llmclient)
        self.assertFalse(page.deployed)
        self.assertEqual(page.mode, "workbench")
        # the url that it will have once it is deployed, not its sandbox url.
        self.assertEqual(page.llmclient.url, self.llmclient.default_url.rstrip("/"))
        self.assertNotIn("/workbench/", page.llmclient.url)
        self.assertEqual(page.snippets.deploy_command, f"smarter deploy llmclient {self.llmclient.name}")
        self.assertEqual(
            page.snippets.deploy_commands,
            f"smarter apply -f {self.llmclient.name}.yaml\nsmarter deploy llmclient {self.llmclient.name}",
        )
        self.assertEqual(page.llmclient.workbench_url, self.llmclient.workbench_url)
        self.assertTrue(
            self.llmclient.workbench_url.endswith(f"/workbench/llm-clients/{self.llmclient.hashed_id}/prompt/")
        )

    def test_the_public_page(self):
        """The public copy of the page has no owner or api keys, even if the page has them."""
        page = deployment_page(self.llmclient)
        self.assertIsNone(page.ownership)
        self.assertIsNone(page.api_keys)
        public = page.public()
        self.assertEqual(public.mode, "public")
        self.assertIsNone(public.ownership)
        self.assertEqual(public.llmclient, page.llmclient)

    def test_example_prompts_that_are_not_strings_are_left_out(self):
        self.llmclient.app_example_prompts = ["What's new?", 3, None]
        self.assertEqual(deployment_page(self.llmclient).llmclient.example_prompts, ["What's new?"])

    def test_the_llmclient_host_serves_the_message_catalog(self):
        match = resolve("/jsi18n/", urlconf=LLMCLIENTS_URLCONF)
        self.assertEqual(match.url_name, "javascript-catalog")
        with override_settings(ALLOWED_HOSTS=["*"]):
            response = match.func(self.request("/jsi18n/"))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("django.gettext", response.content.decode())

    def test_example_prompt(self):
        self.assertEqual(example_prompt(self.llmclient), FIRST_EXAMPLE_PROMPT)
        for prompts in (None, [], ["", "  "]):
            with self.subTest(prompts=prompts):
                self.llmclient.app_example_prompts = prompts
                self.assertEqual(example_prompt(self.llmclient), EXAMPLE_PROMPT)
        self.llmclient.app_example_prompts = ["  ", " What's new? "]
        self.assertEqual(example_prompt(self.llmclient), "What's new?")


class TestCurlCommand(TestAccountMixin):
    """Test the curl commands that the page shows."""

    def test_a_command_without_a_body(self):
        command = curl_command("https://example.com/config/")
        self.assertEqual(
            shlex.split(command.replace("\\\n", "")),
            ["curl", "-X", "POST", "https://example.com/config/", "-H", "Content-Type: application/json"],
        )

    def test_a_command_with_a_body_and_an_api_key(self):
        body = PromptChatApiPromptRequest.model_validate(
            {"messages": [{"role": "user", "content": EXAMPLE_PROMPT}]}
        ).model_dump_json(exclude_none=True)
        command = curl_command("https://example.com/prompt/", body=body, authenticated=True)
        args = shlex.split(command.replace("\\\n", ""))
        self.assertIn("Authorization: Token <YOUR-API-KEY>", args)
        sent = json.loads(args[args.index("-d") + 1])
        self.assertEqual(sent, {"messages": [{"role": "user", "content": EXAMPLE_PROMPT}]})
        PromptChatApiPromptRequest.model_validate(sent)

    def test_a_body_with_a_single_quote(self):
        body = PromptChatApiPromptRequest.model_validate(
            {"messages": [{"role": "user", "content": "What's new?"}]}
        ).model_dump_json(exclude_none=True)
        args = shlex.split(curl_command("https://example.com/prompt/", body=body).replace("\\\n", ""))
        sent = json.loads(args[args.index("-d") + 1])
        self.assertEqual(sent["messages"][0]["content"], "What's new?")


class TestSnippets(TestAccountMixin):
    """Test the example response, and the snippets that put the LLMClient's chat on a web page."""

    def test_example_response_matches_the_contract(self):
        data = json.loads(example_response())
        response = PromptChatApiPromptResponse.model_validate(data)
        self.assertEqual(response.data.status, 200)
        self.assertEqual(response.data.messages[0].role, "assistant")
        self.assertEqual(response.data.messages[0].content, EXAMPLE_RESPONSE_CONTENT)
        self.assertEqual(set(data["data"]), {"status", "messages"})

    def test_embed_html(self):
        html = embed_html("https://example.com")
        self.assertIn(f'<script src="{EMBED_SCRIPT_URL}"', html)
        self.assertIn('data-chatbot="https://example.com/"', html)
        self.assertTrue(html.endswith(" async></script>"))
        self.assertNotIn("data-api-key", html)
        self.assertIn('data-api-key="<YOUR-API-KEY>"', embed_html("https://example.com", authenticated=True))

    def test_react_snippet(self):
        snippet = react_snippet("https://example.com")
        self.assertIn('import { SmarterChat } from "@smarter.sh/ui-chat";', snippet)
        self.assertIn('apiUrl="https://example.com/"', snippet)
        self.assertNotIn("apiKey", snippet)
        self.assertIn("apiKey={import.meta.env.VITE_SMARTER_API_KEY}", react_snippet("https://example.com", True))

    def test_create_api_key_command(self):
        command = create_api_key_command("3141-5926-5359", "stackademy")
        args = shlex.split(command.replace("\\\n", ""))
        self.assertEqual(args[:3], ["python", "manage.py", "create_api_key"])
        self.assertEqual(args[args.index("--account_number") + 1], "3141-5926-5359")
        self.assertEqual(args[args.index("--description") + 1], "stackademy in production")

    def test_api_keys_url(self):
        url = api_keys_url()
        self.assertTrue(url.startswith("http"), url)
        self.assertTrue(url.endswith("/authtoken/"), url)
