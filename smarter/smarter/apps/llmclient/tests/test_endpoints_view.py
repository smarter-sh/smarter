"""Test :mod:`smarter.apps.llmclient.views.endpoints`, the page that a browser sees at a deployed LLMClient's endpoints."""

import json
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
from smarter.apps.llmclient.views.endpoints import (
    EXAMPLE_PROMPT,
    browser_friendly,
    cached_manifest_yaml,
    curl_command,
    highlight_yaml,
    llmclient_manifest,
    manifest_yaml,
)
from smarter.apps.prompt.contract.models import PromptChatApiPromptRequest

MODULE = "smarter.apps.llmclient.views.endpoints"
SWITCH = f"{MODULE}.waffle.switch_is_active"
LLMCLIENTS_URLCONF = "smarter.urls.llmclients"
CONSOLE_URLCONF = "smarter.urls.console"
SYSTEM_ROLE = "You are a helpful assistant.\nAnswer in <b>one</b> sentence."


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
                self.assertIn(self.llmclient.name, html)
                self.assertIn("production api", html)
                self.assertIn(f"{base_url}/config/", html)
                self.assertIn(f"{base_url}/prompt/", html)
                self.assertIn(EXAMPLE_PROMPT, html)
                self.assertIn("What courses are there?", html)
                self.assertIn("https://github.com/smarter-sh", html)
                self.assertIn("smarter-crop.png", html)
                self.assertIn("waffle_switch enable_llmclient_endpoints_page off", html)
                self.assertIn("assets/css/llmclient-endpoints.css", html)
                self.assertIn("js/llmclient/endpoints.js", html)
                self.assertIn('data-clipboard-target="#smarter-prompt-command"', html)
                self.assertIn('data-smarter-copied-label="Copied"', html)
                self.assertNotIn("YOUR-API-KEY", html)
                # escaped, in the description and in the manifest's system role.
                self.assertIn("&lt;courses&gt;", html)
                self.assertIn("&lt;b&gt;one&lt;/b&gt;", html)
                self.assertNotIn("<b>one</b>", html)

    def test_the_manifest_keeps_its_indentation(self):
        html = self.get("/", self.llmclient).content.decode()
        self.assertIn('\n  <span class="yaml-key">name</span>', html)
        self.assertIn('\n    <span class="yaml-key">prompt</span>', html)

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
        html = response.content.decode()
        self.assertIn("Authorization: Token &lt;YOUR-API-KEY&gt;", html)
        self.assertIn("Api key required", html)

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
        html = response.content.decode()
        self.assertNotIn("smarter-manifest", html)
        self.assertIn(EXAMPLE_PROMPT, html)

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


class TestHighlightYaml(TestAccountMixin):
    """Test the YAML highlighter of the page's manifest."""

    def test_keys_values_and_lists(self):
        html = highlight_yaml("kind: LLMClient\ncount: 3\nok: true\nitems:\n  - one\n  - name: two\n# note")
        self.assertIn('<span class="yaml-key">kind</span><span class="yaml-punctuation">:</span>', html)
        self.assertIn('<span class="yaml-string">LLMClient</span>', html)
        self.assertIn('<span class="yaml-literal">3</span>', html)
        self.assertIn('<span class="yaml-literal">true</span>', html)
        self.assertIn('  <span class="yaml-punctuation">- </span><span class="yaml-string">one</span>', html)
        self.assertIn('<span class="yaml-punctuation">- </span><span class="yaml-key">name</span>', html)
        self.assertIn("# note", html)

    def test_literal_blocks(self):
        html = highlight_yaml("role: |\n  line one\n\n  line two\nnext: x")
        self.assertIn('<span class="yaml-block">|</span>', html)
        self.assertIn('<span class="yaml-string">  line one</span>', html)
        self.assertIn('<span class="yaml-string">  line two</span>', html)
        self.assertIn('<span class="yaml-key">next</span>', html)

    def test_everything_is_escaped(self):
        html = highlight_yaml("a: <script>x</script>\n- <b>\n  <i>: |\n    <u>\n<p>")
        for tag in ("<script>", "<b>", "<i>", "<u>", "<p>"):
            self.assertNotIn(tag, html)
        self.assertIn("&lt;script&gt;", html)
        self.assertIn("&lt;p&gt;", html)

    def test_empty_values(self):
        self.assertEqual(
            highlight_yaml("spec:"), '<span class="yaml-key">spec</span><span class="yaml-punctuation">:</span>'
        )


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
