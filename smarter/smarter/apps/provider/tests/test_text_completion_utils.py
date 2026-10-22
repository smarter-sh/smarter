"""Test :mod:`smarter.apps.provider.services.text_completion.utils`."""

import json
from unittest import TestCase

from smarter.apps.provider.services.text_completion import utils
from smarter.common.exceptions import SmarterValueError

MESSAGES = [
    {"role": "system", "content": "You are helpful."},
    {"role": "user", "content": "first"},
    {"role": "assistant", "content": "answer"},
    {"role": "user", "content": "second"},
]


class TestHttpResponseFactory(TestCase):
    """Test the standardized http responses."""

    def test_ok_and_error(self):
        response = utils.http_response_factory(200, {"a": 1})
        self.assertEqual(response["statusCode"], 200)
        self.assertEqual(json.loads(response["body"]), {"a": 1})
        response = utils.http_response_factory(400, {"error": "bad"}, debug_mode=True)
        self.assertEqual(json.loads(response["body"]), {"error": "bad"})

    def test_invalid_status(self):
        for status in (99, 600):
            with self.subTest(status=status), self.assertRaises(SmarterValueError):
                utils.http_response_factory(status, {})

    def test_exception_response_factory(self):
        try:
            raise ValueError("test error")
        except ValueError as e:
            response = utils.exception_response_factory(e, request_meta_data={"x": 1})
        self.assertEqual(response["error"], "test error")
        self.assertIn("ValueError", response["description"])


class TestRequestParsing(TestCase):
    """Test parsing and validating a request body."""

    def test_get_request_body(self):
        self.assertEqual(utils.get_request_body({"messages": MESSAGES})["messages"], MESSAGES)
        self.assertEqual(utils.get_request_body(json.dumps({"messages": MESSAGES}))["messages"], MESSAGES)

    def test_get_request_body_invalid(self):
        for data in ("not json", 42):
            with self.subTest(data=data), self.assertRaises(SmarterValueError):
                utils.get_request_body(data)

    def test_parse_request(self):
        messages, input_text = utils.parse_request({"messages": MESSAGES})
        self.assertEqual(messages, MESSAGES)
        self.assertEqual(input_text, "second")
        messages, _ = utils.parse_request({"messages": json.dumps(MESSAGES)})
        self.assertEqual(messages, MESSAGES)

    def test_parse_request_with_prompt_history(self):
        """Test that a request with prompt history and input text rebuilds its messages."""
        request = {
            "messages": [],
            "input_text": "next",
            "prompt_history": [{"sender": "user", "message": "earlier"}],
        }
        messages, input_text = utils.parse_request(request)
        self.assertEqual(messages, [{"role": "user", "content": "earlier"}, {"role": "user", "content": "next"}])
        self.assertEqual(input_text, "next")

    def test_parse_request_invalid(self):
        for request in (
            {},
            {"messages": "not json"},
            {"messages": "{}"},
            {"messages": ["not a dict"]},
            {"messages": [{"role": "user"}]},
        ):
            with self.subTest(request=request), self.assertRaises(SmarterValueError):
                utils.parse_request(request)


class TestMessageHelpers(TestCase):
    """Test the helpers that read and prepare messages."""

    def test_content_and_messages_for_role(self):
        self.assertEqual(utils.get_content_for_role(MESSAGES, "user"), "second")
        self.assertEqual(utils.get_content_for_role(MESSAGES, "tool"), "")
        self.assertEqual(utils.get_messages_for_role(MESSAGES, "user"), ["first", "second"])
        self.assertIsInstance(utils.get_message_history(MESSAGES), list)

    def test_ensure_system_role_present(self):
        messages = utils.ensure_system_role_present([{"role": "user", "content": "hi"}], "be brief")
        self.assertEqual(messages[0], {"role": "system", "content": "be brief"})
        self.assertEqual(len(utils.ensure_system_role_present(list(MESSAGES), "be brief")), len(MESSAGES))

    def test_ensure_system_role_present_invalid(self):
        for messages, default in (
            ("not a list", "x"),
            (["not a dict"], "x"),
            ([{"role": "user"}], "x"),
            ([{"role": "user", "content": "hi"}], 42),
        ):
            with self.subTest(messages=messages, default=default), self.assertRaises(SmarterValueError):
                utils.ensure_system_role_present(messages, default)


class TestCapMessageHistory(TestCase):
    """Test that the oldest turns of a long thread are left out of the request."""

    THREAD = [
        {"role": "system", "content": "s" * 10},
        {"role": "assistant", "content": "w" * 10},
        {"role": "user", "content": "a" * 100},
        {
            "role": "assistant",
            "content": None,
            "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "f", "arguments": "{}"}}],
        },
        {"role": "tool", "tool_call_id": "call_1", "content": "t" * 100},
        {"role": "assistant", "content": "b" * 100},
        {"role": "user", "content": "c" * 100},
        {"role": "assistant", "content": "d" * 100},
        {"role": "user", "content": "e" * 100},
    ]

    def test_message_characters(self):
        self.assertEqual(utils.message_characters({"role": "user", "content": "abc"}), 3)
        self.assertEqual(utils.message_characters({"role": "assistant", "content": None}), 0)
        self.assertGreater(utils.message_characters(self.THREAD[3]), 0)
        self.assertGreater(utils.message_characters({"role": "user", "content": [{"type": "text"}]}), 0)

    def test_a_short_thread_is_unchanged(self):
        self.assertIs(utils.cap_message_history(self.THREAD, 10_000), self.THREAD)

    def test_the_oldest_whole_turns_are_left_out(self):
        """The first turn, with its tool call and reply, is left out; the system message stays."""
        capped = utils.cap_message_history(self.THREAD, 450)
        self.assertEqual([m["content"][0] for m in capped], ["s", "c", "d", "e"])
        self.assertEqual(len(self.THREAD), 9)

    def test_the_system_prompt_and_latest_turn_are_always_kept(self):
        capped = utils.cap_message_history(self.THREAD, 1)
        self.assertEqual(capped, [self.THREAD[0], self.THREAD[-1]])

    def test_a_single_turn_is_never_cut(self):
        thread = [{"role": "system", "content": "s"}, {"role": "user", "content": "x" * 1000}]
        self.assertIs(utils.cap_message_history(thread, 10), thread)
