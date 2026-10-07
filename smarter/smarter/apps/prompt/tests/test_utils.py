# pylint: disable=wrong-import-position
"""Test configuration Settings class."""

import os
import sys
from pathlib import Path

# python stuff
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402

from smarter.apps.provider.services.text_completion.const import (  # noqa: E402
    OpenAIMessageKeys,
)

# our stuff
from smarter.apps.provider.services.text_completion.utils import (  # noqa: E402
    exception_response_factory,
    get_content_for_role,
    get_message_history,
    get_messages_for_role,
    get_request_body,
    http_response_factory,
    pair_tool_messages,
    parse_request,
)

from ..tests.test_setup import get_test_file  # noqa: E402


class TestUtils(SmarterTestBase):
    """Test utils."""

    # Get the directory of the current script
    here = HERE
    request = get_test_file("json/passthrough_openai_v2_request.json")
    response = get_test_file("json/passthrough_openai_v2_response.json")

    def test_http_response_factory(self):
        """Test test_http_response_factory."""
        retval = http_response_factory(200, self.response)
        self.assertEqual(retval["statusCode"], 200)
        self.assertEqual(retval["body"], json.dumps(self.response))
        self.assertEqual(retval["isBase64Encoded"], False)
        self.assertEqual(retval["headers"]["Content-Type"], "application/json")

    def test_exception_response_factory(self):
        """Test exception_response_factory."""
        try:
            raise AssertionError("test")
        except AssertionError as exception:
            retval = exception_response_factory(exception)
            self.assertIn("error", retval)
            self.assertIn("description", retval)

    def test_get_request_body(self):
        """Test get_request_body."""
        request_body = get_request_body(self.request)
        self.assertEqual(request_body, self.request)
        self.assertIn("messages", request_body)

    def test_parse_request(self):
        """Test parse_request."""
        request_body = get_request_body(self.request)
        messages, input_text = parse_request(request_body)
        self.assertEqual(input_text, "return the integer value 42.")
        self.assertEqual(len(messages), 2)

    def test_get_content_for_role(self):
        """Test get_content_for_role."""
        request_body = get_request_body(self.request)
        messages, _ = parse_request(request_body)
        system_message = get_content_for_role(messages, OpenAIMessageKeys.SYSTEM_MESSAGE_KEY)
        user_message = get_content_for_role(messages, OpenAIMessageKeys.USER_MESSAGE_KEY)
        self.assertEqual(system_message, "you always return the integer value 42.")
        self.assertEqual(user_message, "return the integer value 42.")

    def test_get_message_history(self):
        """Test get_message_history."""
        request_body = get_request_body(self.request)
        messages, _ = parse_request(request_body)
        message_history = get_message_history(messages)
        self.assertIsInstance(message_history, list)
        self.assertEqual(len(message_history), 1)
        self.assertEqual(message_history[0]["role"], "user")
        self.assertEqual(message_history[0]["content"], "return the integer value 42.")

    def test_get_messages_for_role(self):
        """Test get_messages_for_role."""
        request_body = get_request_body(self.request)
        messages, _ = parse_request(request_body)
        message_history = get_message_history(messages)
        self.assertIsInstance(message_history, list)
        user_messages = get_messages_for_role(message_history, OpenAIMessageKeys.USER_MESSAGE_KEY)
        self.assertEqual(len(user_messages), 1)
        self.assertEqual(user_messages[0], "return the integer value 42.")


def tool_call(call_id: str) -> dict:
    """Return an assistant tool call."""
    return {"id": call_id, "type": "function", "function": {"name": "example_tool", "arguments": "{}"}}


class TestPairToolMessages(SmarterTestBase):
    """Test that pair_tool_messages() pairs every tool call with its tool reply, as OpenAI requires."""

    system = {"role": "system", "content": "You are helpful."}
    user = {"role": "user", "content": "Tell me about Smarter"}
    reply = {"role": "assistant", "content": "Smarter is a platform."}

    def test_paired_thread_is_unchanged(self):
        """Test that a thread whose tool calls are all answered is returned unchanged."""
        messages = [
            self.system,
            self.user,
            {"role": "assistant", "content": None, "tool_calls": [tool_call("a"), tool_call("b")]},
            {"role": "tool", "tool_call_id": "a", "content": "A"},
            {"role": "tool", "tool_call_id": "b", "content": "B"},
            self.reply,
        ]
        self.assertEqual(pair_tool_messages(messages), messages)

    def test_orphan_tool_message_is_removed(self):
        """Test that a tool reply without its assistant tool call, as the chat window sends it, is removed."""
        messages = [self.system, self.user, {"role": "tool", "tool_call_id": "a", "content": "A"}, self.reply]
        self.assertEqual(pair_tool_messages(messages), [self.system, self.user, self.reply])

    def test_unanswered_tool_call_is_removed(self):
        """Test that a tool call without a reply is removed, and that the assistant message stays valid."""
        partly = {"role": "assistant", "content": None, "tool_calls": [tool_call("a"), tool_call("b")]}
        answer = {"role": "tool", "tool_call_id": "a", "content": "A"}
        retval = pair_tool_messages([self.user, partly, answer])
        self.assertEqual([call["id"] for call in retval[1]["tool_calls"]], ["a"])
        self.assertEqual(retval[2], answer)
        self.assertEqual(len(partly["tool_calls"]), 2, "the caller's message must not be modified")

        unanswered = {"role": "assistant", "content": None, "tool_calls": [tool_call("a")]}
        retval = pair_tool_messages([self.user, unanswered, self.user])
        self.assertNotIn("tool_calls", retval[1])
        self.assertEqual(retval[1]["content"], "")

    def test_reply_to_another_call_is_removed(self):
        """Test that a tool reply that answers no tool call of the preceding assistant message is removed."""
        messages = [
            {"role": "assistant", "content": None, "tool_calls": [tool_call("a")]},
            {"role": "tool", "tool_call_id": "a", "content": "A"},
            {"role": "tool", "tool_call_id": "z", "content": "Z"},
        ]
        self.assertEqual(pair_tool_messages(messages), messages[:2])
