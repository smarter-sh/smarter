"""
Test the provider request api: a chat session's conversation, as the request body that Smarter sends to the LLM provider.

See :mod:`smarter.apps.prompt.views.detailviews.prompt_provider_request_view`.
"""

import json
import secrets
from http import HTTPStatus
from pathlib import Path
from unittest.mock import MagicMock, patch

import yaml
from django.contrib.auth.models import AnonymousUser
from django.test import Client, RequestFactory, override_settings
from pydantic import ValidationError

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.api.v1.urls import LLMClientApiV1ReverseViews
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.contract.models import (
    PromptChatApiErrorResponse,
    PromptChatApiProviderRequest,
    PromptChatApiProviderRequestResponse,
)
from smarter.apps.prompt.models import Prompt, PromptHistory
from smarter.apps.prompt.tasks import create_prompt_history
from smarter.apps.prompt.views.detailviews import prompt_provider_request_view as module
from smarter.apps.prompt.views.detailviews.prompt_provider_request_view import (
    PromptProviderRequestView,
    llmclient_request_settings,
    provider_request,
)
from smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider import (
    MARKDOWN_SYSTEM_PROMPT,
)
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.shortcuts import reverse
from smarter.lib.openai import model_quirks

MODEL = "gpt-test"
TOOL = {
    "type": "function",
    "function": {
        "name": "smarter_plugin_0000000001",
        "description": "A test tool.",
        "parameters": {"type": "object", "properties": {"q": {"type": "string"}}},
    },
}
TOOL_CALL = {"id": "call_1", "type": "function", "function": {"name": "smarter_plugin_0000000001", "arguments": "{}"}}

SAVED_REQUEST = {
    "api_url": "https://api.example.com/v1/",
    "api_key": "****ABCD",
    "model": MODEL,
    "temperature": 0.5,
    "max_completion_tokens": 512,
    "tools": [TOOL],
    "tool_choice": "auto",
    "messages": [{"role": "system", "content": "the first iteration's messages", "smarter_is_new": False}],
}
"""A saved first request, as OpenAISmarterClient.prep_first_request() saves it."""

SAVED_MESSAGES = [
    {"role": "system", "content": "You are a test.", "smarter_is_new": False},
    {"role": "smarter", "content": "Prompt configuration: api_key=****ABCD", "smarter_is_new": False},
    {"role": "user", "content": "hello", "smarter_is_new": False},
    {"role": "assistant", "content": None, "tool_calls": [TOOL_CALL], "refusal": None, "smarter_is_new": True},
    {"role": "tool", "content": "a result", "tool_call_id": "call_1", "name": TOOL_CALL["function"]["name"]},
    {"role": "assistant", "content": "hi", "annotations": [], "smarter_is_new": True},
    {"role": "smarter_error", "content": "a failure", "smarter_is_new": True},
]
"""A saved conversation, with Smarter's own messages and fields."""


class TestPromptProviderRequestView(TestAccountMixin):
    """Test the provider request api, by hashed id and by id, as the workbench calls it."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_provider_request_{self.hash_suffix}",
            user_profile=self.user_profile,
            default_model=MODEL,
            default_temperature=0.25,
            default_max_tokens=256,
            default_system_role="You are a test.",
            app_welcome_message="Welcome!",
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.addCleanup(Prompt.objects.filter(llmclient=self.llmclient).delete)
        self.client = Client()
        self.client.force_login(self.admin_user)

    def url(self, session_key: str, by_id: bool = False) -> str:
        """The provider request api's url, with the chat session's key."""
        if by_id:
            name = LLMClientApiV1ReverseViews.provider_request_view_by_id
            kwargs = {"llmclient_id": self.llmclient.pk}
        else:
            name = LLMClientApiV1ReverseViews.provider_request_view_by_hashed_id
            kwargs = {"hashed_id": self.llmclient.hashed_id}
        path = reverse(f"{LLMClientApiV1ReverseViews.namespace}:{name}", kwargs=kwargs)
        return f"{path}?session_key={session_key}"

    def create_prompt(self, request=None, messages=None) -> Prompt:
        """A chat session, with a saved prompt if a request or messages are given."""
        prompt = Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=self.user_profile,
            llmclient=self.llmclient,
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.example.com",
        )
        if request is not None or messages is not None:
            PromptHistory.objects.create(prompt=prompt, request=request, response={}, messages=messages)
        return prompt

    def post(self, url: str):
        """POST to the api, and return the response and its JSON."""
        response = self.client.post(url, data="{}", content_type="application/json")
        return response, json.loads(response.content)

    def test_urls(self):
        """The api is beside the LLMClient's config api."""
        api = f"/api/v1/llm-clients/{self.llmclient.hashed_id}/"
        self.assertTrue(self.url("x").startswith(api + "provider-request/"))
        self.assertTrue(
            self.url("x", by_id=True).startswith(f"/api/v1/llm-clients/{self.llmclient.pk}/provider-request/")
        )

    def test_after_a_prompt(self):
        """The conversation, with the latest prompt's settings and tools, and nothing of Smarter's own."""
        prompt = self.create_prompt(request=SAVED_REQUEST, messages=SAVED_MESSAGES)
        response, payload = self.post(self.url(prompt.session_key))
        self.assertEqual(response.status_code, HTTPStatus.OK, payload)
        PromptChatApiProviderRequestResponse.model_validate(payload)
        body = payload["data"]
        self.assertEqual(body["model"], MODEL)
        self.assertEqual(body["temperature"], 0.5)
        self.assertEqual(body["max_completion_tokens"], 512)
        self.assertEqual(body["tools"], [TOOL])
        self.assertEqual(body["tool_choice"], "auto")
        roles = [message["role"] for message in body["messages"]]
        self.assertEqual(roles, ["system", "user", "assistant", "tool", "assistant"])
        self.assertTrue(body["messages"][0]["content"].endswith(MARKDOWN_SYSTEM_PROMPT))
        self.assertEqual(body["messages"][2], {"role": "assistant", "tool_calls": [TOOL_CALL]})
        self.assertEqual(body["messages"][4], {"role": "assistant", "content": "hi", "annotations": []})
        content = json.dumps(body)
        for smarter_content in ("smarter_is_new", "smarter_error", "api_url", "api_key", "****ABCD", "a failure"):
            self.assertNotIn(smarter_content, content)

    def test_by_id(self):
        prompt = self.create_prompt(request=SAVED_REQUEST, messages=SAVED_MESSAGES)
        response, payload = self.post(self.url(prompt.session_key, by_id=True))
        self.assertEqual(response.status_code, HTTPStatus.OK, payload)
        self.assertEqual(payload["data"]["model"], MODEL)

    def test_before_a_prompt(self):
        """A session that has sent no prompt is the LLMClient's introduction, with its settings and no tools."""
        prompt = self.create_prompt()
        response, payload = self.post(self.url(prompt.session_key))
        self.assertEqual(response.status_code, HTTPStatus.OK, payload)
        body = payload["data"]
        self.assertEqual(
            (body["model"], body["temperature"], body["max_completion_tokens"]),
            (MODEL, 0.25, 256),
        )
        self.assertNotIn("tools", body)
        self.assertEqual([message["role"] for message in body["messages"]], ["system", "assistant"])
        self.assertIn("You are a test.", body["messages"][0]["content"])
        self.assertEqual(body["messages"][1]["content"], "Welcome!")

    def test_a_new_session(self):
        """A request without a session key starts a session, as the config api does."""
        path = self.url("").split("?", maxsplit=1)[0]
        response, payload = self.post(path)
        self.assertEqual(response.status_code, HTTPStatus.OK, payload)
        self.assertEqual(payload["data"]["messages"][0]["role"], "system")

    def test_an_anonymous_user_is_refused(self):
        """A 404, as for an LLMClient that doesn't exist, so that it can't be discovered."""
        prompt = self.create_prompt(request=SAVED_REQUEST, messages=SAVED_MESSAGES)
        self.client.logout()
        response, payload = self.post(self.url(prompt.session_key))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        PromptChatApiErrorResponse.model_validate(payload)

    def test_another_account_is_refused(self):
        prompt = self.create_prompt(request=SAVED_REQUEST, messages=SAVED_MESSAGES)
        other_admin_user, _, _ = admin_user_factory()
        # admin_user_factory() users are superusers, who may read every account's resources.
        other_admin_user.is_superuser = False
        other_admin_user.save()
        self.client.force_login(other_admin_user)
        response, _ = self.post(self.url(prompt.session_key))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_a_request_that_breaks_the_contract(self):
        prompt = self.create_prompt(request=SAVED_REQUEST, messages=SAVED_MESSAGES)
        error = ValidationError.from_exception_data("PromptChatApiProviderRequest", [])
        with patch.object(module, "provider_request", side_effect=error):
            response, payload = self.post(self.url(prompt.session_key))
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
        self.assertIn("could not be built", json.dumps(payload))

    def test_a_deployed_llmclients_own_host_is_refused(self):
        """The request holds the system prompt and tool definitions, so a deployed LLMClient's host never returns it."""
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=True)
        self.llmclient.refresh_from_db()
        request = RequestFactory().post(
            "/provider-request/", data={}, content_type="application/json", HTTP_HOST="test.api.example.com"
        )
        request.user = AnonymousUser()
        with (
            override_settings(ALLOWED_HOSTS=["*"]),
            patch(
                "smarter.apps.prompt.views.detailviews.prompt_config_view.get_cached_llmclient_by_request",
                return_value=self.llmclient,
            ),
        ):
            response = PromptProviderRequestView.as_view()(request)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_without_a_session(self):
        """The view's provider_request() is None without a session, and the api answers 404."""
        view = PromptProviderRequestView()
        view.session = None
        self.assertIsNone(view.provider_request())
        view.resolved_by_id = True
        view.thing = None
        view.command = None
        request = RequestFactory().post("/")
        with patch.object(PromptProviderRequestView, "provider_request", return_value=None):
            response = view.config_response(request)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertIn("PromptProviderRequestView", view.formatted_class_name)


class TestProviderRequestOfARealPrompt(TestAccountMixin):
    """
    The download of a real prompt that called a tool, checked against that prompt's own request and response.

    The prompt (tests/data/stackademy_sql_tool_call.yaml) is saved as the platform saves every prompt, by the
    create_prompt_history task, in the session that the config api gave the chat. The download must be the prompt's
    request, with the response's new messages appended: the tools that were presented, each tool call, each tool's
    result and the final answer, in a request that an OpenAI-compatible api accepts.
    """

    def setUp(self):
        super().setUp()
        with open(Path(__file__).parent / "data" / "stackademy_sql_tool_call.yaml", encoding="utf-8") as file:
            self.saved = yaml.safe_load(file)
        self.request = self.saved["request"]
        self.response = self.saved["response"]
        self.llmclient = self.create_llmclient("stackademy_sql")
        self.client = Client()
        self.client.force_login(self.admin_user)

    def create_llmclient(self, name: str) -> LLMClient:
        """An LLMClient of the test's account, deleted with its sessions after the test."""
        llmclient = LLMClient.objects.create(
            name=f"test_{name}_{self.hash_suffix}", user_profile=self.user_profile, default_model=MODEL
        )
        self.addCleanup(LLMClient.objects.filter(pk=llmclient.pk).delete)
        self.addCleanup(Prompt.objects.filter(llmclient=llmclient).delete)
        return llmclient

    def post(self, view_name: str, session_key: str) -> dict:
        """POST the chat's session key to one of the LLMClient's chat apis, as Smarter Chat does, and return its data."""
        path = reverse(
            f"{LLMClientApiV1ReverseViews.namespace}:{view_name}", kwargs={"hashed_id": self.llmclient.hashed_id}
        )
        response = self.client.post(
            f"{path}?session_key={session_key}",
            data=json.dumps({"session_key": session_key}),
            content_type="application/json",
        )
        payload = json.loads(response.content)
        self.assertEqual(response.status_code, HTTPStatus.OK, payload)
        return payload["data"]

    def download_after_the_prompt(self) -> dict:
        """
        The chat's session from the config api, the prompt saved in it, and the session's download.

        The chat starts with another LLMClient's session key, as a browser's session cookie can hold, so the config
        api gives it a new session.
        """
        other_session_key = secrets.token_hex(32)
        Prompt.objects.create(
            session_key=other_session_key,
            user_profile=self.user_profile,
            llmclient=self.create_llmclient("another_llmclient"),
            ip_address="192.1.1.1",
            user_agent="unit test",
            url="https://www.example.com",
        )
        session_key = self.post(LLMClientApiV1ReverseViews.chat_config_view_by_hashed_id, other_session_key)[
            "session_key"
        ]
        self.assertNotEqual(session_key, other_session_key)
        prompt = Prompt.objects.get(session_key=session_key)
        self.assertEqual(prompt.llmclient, self.llmclient)
        # as the prompt_finished receiver queues it, run as a Celery worker runs it.
        create_prompt_history(prompt.id, self.request, self.response, self.saved["messages"])
        body = self.post(LLMClientApiV1ReverseViews.provider_request_view_by_hashed_id, session_key)
        PromptChatApiProviderRequest.model_validate(body)
        return body

    @staticmethod
    def provider_messages_of(messages: list[dict]) -> list[dict]:
        """
        The messages that an LLM provider receives: without Smarter's own messages and fields, and without the null.

        fields that the api leaves out, e.g. a tool-calling message's content.
        """
        provider_roles = ("system", "user", "assistant", "tool")
        return [
            {key: value for key, value in message.items() if not key.startswith("smarter") and value is not None}
            for message in messages
            if message["role"] in provider_roles
        ]

    def test_the_test_data(self):
        """The prompt presented a tool, called it, and answered from its result, so each must be in the download."""
        new_messages = self.response["smarter"]["messages"]
        self.assertTrue(self.request["tools"])
        self.assertTrue([m for m in new_messages if m["role"] == "assistant" and m.get("tool_calls")])
        self.assertTrue([m for m in new_messages if m["role"] == "tool"])
        self.assertTrue(self.response["choices"][0]["message"]["content"])

    def test_the_request_and_the_response_are_in_the_download(self):
        """The download is the prompt's request, with the response's new messages appended."""
        body = self.download_after_the_prompt()
        expected = self.provider_messages_of(self.request["messages"] + self.response["smarter"]["messages"])
        downloaded = body["messages"]
        self.assertEqual([m["role"] for m in downloaded], [m["role"] for m in expected])
        self.assertEqual(downloaded, expected)
        # the system prompt, as the LLM received it, with the chat's Markdown instructions, once.
        self.assertEqual(downloaded[0]["content"].count(MARKDOWN_SYSTEM_PROMPT), 1)

    def test_the_tools_that_were_presented(self):
        body = self.download_after_the_prompt()
        self.assertEqual(body["tools"], self.request["tools"])
        self.assertEqual(body["tool_choice"], self.request["tool_choice"])
        self.assertEqual(body["model"], self.request["model"])

    def test_each_tool_call_and_its_result(self):
        """Each tool call, with its arguments, is followed by its tool's result, as OpenAI requires."""
        body = self.download_after_the_prompt()
        new_messages = self.response["smarter"]["messages"]
        tool_calls = [call for m in new_messages if m["role"] == "assistant" for call in m.get("tool_calls") or []]
        results = {m["tool_call_id"]: m["content"] for m in new_messages if m["role"] == "tool"}
        downloaded = body["messages"]
        for call in tool_calls:
            calling = [i for i, m in enumerate(downloaded) if call in (m.get("tool_calls") or [])]
            self.assertEqual(len(calling), 1, f"tool call {call['id']} is not in the download")
            index = calling[0]
            replies = {m["tool_call_id"]: m for m in downloaded[index + 1 :] if m["role"] == "tool"}
            self.assertIn(call["id"], replies, f"the result of tool call {call['id']} is not in the download")
            self.assertEqual(replies[call["id"]]["content"], results[call["id"]])

    def test_the_users_prompt_and_the_final_answer(self):
        body = self.download_after_the_prompt()
        downloaded = body["messages"]
        user_prompts = [m["content"] for m in self.request["messages"] if m["role"] == "user"]
        self.assertEqual([m["content"] for m in downloaded if m["role"] == "user"], user_prompts)
        self.assertEqual(downloaded[-1]["role"], "assistant")
        self.assertEqual(downloaded[-1]["content"], self.response["choices"][0]["message"]["content"])

    def test_nothing_of_smarters_own(self):
        """An OpenAI-compatible api rejects Smarter's own roles and fields, and the api key never leaves the platform."""
        body = self.download_after_the_prompt()
        self.assertEqual({m["role"] for m in body["messages"]} - {"system", "user", "assistant", "tool"}, set())
        content = json.dumps(body)
        for smarter_content in ("smarter_is_new", '"role": "smarter"', "api_url", "api_key", self.request["api_key"]):
            self.assertNotIn(smarter_content, content)


class TestProviderRequest(TestAccountMixin):
    """Test provider_request() and its helpers, without the api."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_provider_request_fn_{self.hash_suffix}", user_profile=self.user_profile, default_model=MODEL
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)

    def test_the_first_iterations_messages_without_the_conversation(self):
        """An older history without its conversation's messages falls back on the saved request's."""
        history = MagicMock(request=SAVED_REQUEST, messages=None)
        body = provider_request(history, self.llmclient)
        self.assertEqual(body.messages[0].content, f"the first iteration's messages\n\n{MARKDOWN_SYSTEM_PROMPT}")

    def test_model_quirks_apply(self):
        """The model's quirks apply, as they do to every request that Smarter sends."""
        history = MagicMock(request=SAVED_REQUEST, messages=SAVED_MESSAGES)
        with (
            patch.object(model_quirks, "TOOLS_REQUIRE_NO_REASONING_MODELS", {MODEL}),
            patch.object(model_quirks, "DEFAULT_TEMPERATURE_ONLY_MODELS", set()),
        ):
            body = provider_request(history, self.llmclient)
        self.assertEqual(body.reasoning_effort, "none")
        self.assertEqual(body.temperature, 0.5)
        with (
            patch.object(model_quirks, "TOOLS_REQUIRE_NO_REASONING_MODELS", set()),
            patch.object(model_quirks, "DEFAULT_TEMPERATURE_ONLY_MODELS", {MODEL}),
        ):
            body = provider_request(history, self.llmclient)
        self.assertIsNone(body.temperature)
        self.assertIsNone(body.reasoning_effort)
        self.assertIsInstance(body, PromptChatApiProviderRequest)

    def test_the_platforms_defaults(self):
        """An LLMClient without its own settings gets its provider's default model and the platform's defaults."""
        self.llmclient.default_model = ""
        self.llmclient.default_temperature = None
        self.llmclient.default_max_tokens = None
        provider = MagicMock(default_model="gpt-default")
        with patch.object(
            module.openai_compatible_client, "get_client_orm_by_provider_name_and_user", return_value=provider
        ):
            settings = llmclient_request_settings(self.llmclient)
        self.assertEqual(
            settings,
            {
                "model": "gpt-default",
                "temperature": smarter_settings.llm_default_temperature,
                "max_completion_tokens": smarter_settings.llm_default_max_tokens,
            },
        )

    def test_a_provider_that_is_not_found(self):
        """Without a provider, the model is unknown, and the request has none."""
        self.llmclient.default_model = ""
        with (
            patch.object(
                module.openai_compatible_client,
                "get_client_orm_by_provider_name_and_user",
                side_effect=SmarterValueError("not found"),
            ),
            patch.object(module, "logger") as logger,
        ):
            settings = llmclient_request_settings(self.llmclient)
        self.assertIsNone(settings["model"])
        logger.warning.assert_called_once()
