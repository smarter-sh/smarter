"""Tests of smarter.lib.cache.tool_results."""

from unittest.mock import MagicMock

from pydantic import BaseModel

from smarter.lib.cache.tool_results import (
    CachedToolResult,
    cached_tool_call,
    canonical_arguments,
    is_error_result,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class Arguments(BaseModel):
    """The arguments of a test tool."""

    query: str
    limit: int = 8


class TestToolResults(SmarterTestBase):
    """Test the one cache of tool call results."""

    def key(self, *parts) -> tuple:
        """Return a key that no other test uses."""
        return (self.id(), *parts)

    def test_canonical_arguments(self):
        """JSON arguments are keyed with sorted keys, and a model by its fields."""
        self.assertEqual(canonical_arguments({"b": 1, "a": 2}), canonical_arguments({"a": 2, "b": 1}))
        self.assertEqual(canonical_arguments(Arguments(query="dns")), '{"query":"dns","limit":8}')

    def test_a_result_is_cached_by_its_key_and_arguments(self):
        """The same call runs once, and says that its second result was cached."""
        call = MagicMock(return_value="result")
        first = cached_tool_call("test", self.key("tool"), {"a": 1}, 60, call)
        second = cached_tool_call("test", self.key("tool"), {"a": 1}, 60, call)
        self.assertEqual(first, CachedToolResult(value="result", cached=False))
        self.assertEqual(second, CachedToolResult(value="result", cached=True))
        self.assertEqual(call.call_count, 1)

    def test_namespaces_keys_and_arguments_are_separate(self):
        """Another namespace, key or arguments runs the call again."""
        call = MagicMock(return_value="result")
        cached_tool_call("test", self.key("tool"), {"a": 1}, 60, call)
        cached_tool_call("other", self.key("tool"), {"a": 1}, 60, call)
        cached_tool_call("test", self.key("other tool"), {"a": 1}, 60, call)
        cached_tool_call("test", self.key("tool"), {"a": 2}, 60, call)
        self.assertEqual(call.call_count, 4)

    def test_an_error_is_never_cached(self):
        """A call that raises is run again on the next call."""
        call = MagicMock(side_effect=ValueError("the tool failed"))
        for _ in range(2):
            with self.assertRaises(ValueError):
                cached_tool_call("test", self.key("tool"), {}, 60, call)
        self.assertEqual(call.call_count, 2)

    def test_a_returned_error_is_never_cached(self):
        """A call that returns an error, rather than raising it, is returned, and run again on the next call."""
        for error in ({"error": "no such city"}, "Error: the server is down", '{"error": "budget_exceeded"}'):
            with self.subTest(error=error):
                call = MagicMock(return_value=error)
                results = [cached_tool_call("test", self.key("tool", str(error)), {}, 60, call) for _ in range(2)]
                self.assertEqual(results, [CachedToolResult(value=error, cached=False)] * 2)
                self.assertEqual(call.call_count, 2)

    def test_a_caller_can_say_what_an_error_is(self):
        """An is_error check replaces the default conventions."""
        call = MagicMock(return_value={"status": "failed"})
        for _ in range(2):
            cached_tool_call("test", self.key("tool"), {}, 60, call, is_error=lambda value: value["status"] == "failed")
        self.assertEqual(call.call_count, 2)
        # without the check, the same result is not an error, and is cached.
        call.reset_mock()
        for _ in range(2):
            cached_tool_call("test", self.key("other tool"), {}, 60, call)
        self.assertEqual(call.call_count, 1)

    def test_is_error_result(self):
        """Errors are text that begins with Error:, or a JSON object, or its text, with an error key."""
        for value in ("Error: down", "  Error: down", {"error": "x"}, '{"error": "x"}', ' {"error": null}'):
            with self.subTest(value=value):
                self.assertTrue(is_error_result(value))
        for value in ("rows", "", '{"errors": 1}', '{"error" broken', "an Error: in the text", {"result": 2}, 3, None):
            with self.subTest(value=value):
                self.assertFalse(is_error_result(value))

    def test_timeout_zero_skips_the_cache(self):
        """A timeout of 0 runs the call every time."""
        call = MagicMock(return_value="result")
        results = [cached_tool_call("test", self.key("tool"), {}, 0, call) for _ in range(2)]
        self.assertEqual(results, [CachedToolResult(value="result", cached=False)] * 2)
        self.assertEqual(call.call_count, 2)
