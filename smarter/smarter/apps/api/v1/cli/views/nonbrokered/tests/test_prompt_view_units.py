"""Unit tests of ApiV1CliPromptApiView's message list, error message and validation helpers, with its request-derived properties patched."""

from unittest.mock import PropertyMock, patch

from django.http import QueryDict

from smarter.apps.api.v1.cli.views.nonbrokered.prompt import (
    APIV1CLIChatViewError,
    ApiV1CliPromptApiView,
)
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

SESSION_KEY = "9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126"


class TestPromptViewUnits(SmarterTestBase):
    """Test ApiV1CliPromptApiView's helpers without a request."""

    def view(self, data=None, params: str = "", is_config: bool = False, chat_config=None) -> ApiV1CliPromptApiView:
        """Return a view whose data, params and is_config are patched."""
        for name, value in (("data", data), ("params", QueryDict(params)), ("is_config", is_config)):
            patcher = patch.object(ApiV1CliPromptApiView, name, new_callable=PropertyMock, return_value=value)
            patcher.start()
            self.addCleanup(patcher.stop)
        view = ApiV1CliPromptApiView()
        view._prompt = None
        view._messages = None
        view._chat_config = chat_config or {}
        return view

    def test_prompt(self):
        """The prompt comes from the request body, is required, and isn't used by config views."""
        self.assertEqual(self.view(data={"prompt": "hello"}).prompt, "hello")

    def test_prompt_is_required(self):
        with self.assertRaises(APIV1CLIChatViewError):
            _ = self.view(data={}).prompt

    def test_config_views_have_no_prompt(self):
        self.assertIsNone(self.view(data={}, is_config=True).prompt)

    def test_new_session(self):
        """New_session is a true/false url param."""
        self.assertTrue(self.view(params="new_session=true").new_session)
        self.assertFalse(self.view(params="new_session=false").new_session)

    def test_new_session_rejects_other_values(self):
        with self.assertRaises(APIV1CLIChatViewError):
            _ = self.view(params="new_session=maybe").new_session

    def test_new_message_list_with_welcome_message(self):
        """A welcome message and example prompts add an assistant message between the system and user messages."""
        chat_config = {
            "llmclient": {
                "default_system_role": "You are a test.",
                "app_welcome_message": "Welcome",
                "app_example_prompts": ["one", "two"],
                "app_assistant": "a test assistant",
            }
        }
        messages = self.view(data={"prompt": "hello"}, chat_config=chat_config).new_message_list_factory()
        self.assertEqual([m["role"] for m in messages], ["system", "assistant", "user"])
        self.assertEqual(messages[0]["content"], "You are a test.")
        self.assertIn("    - two", messages[1]["content"])
        self.assertIn("a test assistant", messages[1]["content"])
        self.assertEqual(messages[2]["content"], "hello")

    def test_messages_for_a_new_session(self):
        """A new session starts a new message list."""
        view = self.view(data={"prompt": "hello"}, params="new_session=true")
        self.assertEqual([m["role"] for m in view.messages], ["system", "user"])
        self.assertIs(view.messages, view.messages)

    def test_messages_from_the_request(self):
        """Messages in the request body are continued with the prompt."""
        history = [{"role": "system", "content": "s"}]
        view = self.view(data={"prompt": "hello", "messages": history})
        view.messages  # pylint: disable=pointless-statement
        self.assertEqual(history[-1], {"role": "user", "content": "hello"})

    def test_url_llmclient(self):
        """The llmclient url comes from the prompt config."""
        view = self.view(data={}, chat_config={"llmclient": {"url_llmclient": "https://example.com/"}})
        self.assertEqual(view.url_llmclient, "https://example.com/")
        self.assertEqual(view.chat_config["llmclient"]["url_llmclient"], "https://example.com/")

    def test_chat_request_factory_errors(self):
        """A request can't be made without a url or with a body that isn't a dict."""
        view = self.view(data={})
        with patch.object(ApiV1CliPromptApiView, "parsed_url", new_callable=PropertyMock, return_value=None):
            with self.assertRaises(SmarterConfigurationError):
                view.chat_request_factory(request_body={})
        with patch.object(ApiV1CliPromptApiView, "parsed_url", new_callable=PropertyMock, return_value="x"):
            with self.assertRaises(SmarterConfigurationError):
                view.chat_request_factory(request_body=[])  # type: ignore[arg-type]

    def test_prompt_error_message(self):
        """The error message comes from the provider's error body, else the status code."""
        message = ApiV1CliPromptApiView.prompt_error_message
        self.assertEqual(message({"data": {"body": {"error": {"message": "bad key"}}}}), "bad key")
        self.assertEqual(message({"data": {"body": json.dumps({"error": {"message": "quota"}})}}), "quota")
        self.assertEqual(message({"data": {"body": "not json"}}), "not json")
        self.assertIn("429", message({"data": {"statusCode": 429}}))
        self.assertIn("unknown", message({}))

    def test_validate(self):
        """Validate() needs a prompt, a list of messages and a valid session key."""
        cases = (
            {"messages": "[1, 2"},
            {"prompt": "hello", "messages": "[1, 2"},
            {"prompt": "hello", "messages": json.dumps({"not": "a list"})},
            {"prompt": "hello", "session_key": "not-a-session-key"},
        )
        for data in cases:
            with self.subTest(data=data):
                view = self.view(data=data)
                with self.assertRaises(Exception):
                    view.validate()

    def test_validate_ok(self):
        """A prompt with a message list and a valid session key validates."""
        view = self.view(data={"prompt": "hello", "messages": json.dumps([]), "session_key": SESSION_KEY})
        view.validate()

    def test_chat_and_prompt_history(self):
        """The Prompt and its latest history are looked up by session key, once."""
        view = self.view(data={})
        view._chat = None
        view._chat_history = None
        prompt = object()
        history = object()
        module = "smarter.apps.api.v1.cli.views.nonbrokered.prompt"
        with (
            patch.object(ApiV1CliPromptApiView, "session_key", new_callable=PropertyMock, return_value=SESSION_KEY),
            patch(f"{module}.Prompt.objects.filter") as prompt_filter,
            patch(f"{module}.PromptHistory.objects.filter") as history_filter,
        ):
            prompt_filter.return_value.first.return_value = prompt
            history_filter.return_value.latest.return_value = history
            self.assertIs(view.prompt_history, history)
            self.assertIs(view.chat, prompt)
        prompt_filter.assert_called_once_with(session_key=SESSION_KEY)
        history_filter.assert_called_once_with(prompt=prompt)
