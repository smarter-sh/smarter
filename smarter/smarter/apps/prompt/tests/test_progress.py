"""Tests for smarter.apps.prompt.progress: a prompt's progress, as Server-Sent Events."""

import asyncio
import json
import time
from http import HTTPStatus
from unittest import TestCase
from unittest.mock import MagicMock, patch

from django.http import HttpResponse, JsonResponse
from django.test import RequestFactory

from smarter.apps.mcpclient.signals import (
    mcpclient_tool_called,
    mcpclient_tool_failed,
    mcpclient_tool_responded,
)
from smarter.apps.prompt import progress
from smarter.apps.prompt.progress import (
    PromptProgressEvents,
    emit,
    progress_sink,
    prompt_event_stream,
    prompt_event_stream_response,
    wants_event_stream,
)
from smarter.apps.prompt.signals import (
    chat_plugin_called,
    chat_request,
    llm_tool_requested,
    llm_tool_responded,
)

TOOL_CALL = {"id": "call_1", "type": "function", "function": {"name": "get_current_weather", "arguments": '{"a": 1}'}}


def process_tool_call():
    """A stand-in for the provider's tool call loop, which sends the tool signals."""


def get_current_weather():
    """A stand-in for a built-in function, which sends the tool signals too."""


def collect(stream) -> list[str]:
    """The frames of an async SSE stream."""

    async def run():
        return [frame.decode() if isinstance(frame, bytes) else frame async for frame in stream]

    return asyncio.run(run())


def events(frames: list[str], name: str) -> list[dict]:
    """The data of the frames of the named event."""
    prefix = f"event: {name}\ndata: "
    return [json.loads(frame[len(prefix) :]) for frame in frames if frame.startswith(prefix)]


class TestEmit(TestCase):
    """Test emit() and progress_sink()."""

    def test_emit_without_a_sink_does_nothing(self):
        emit(PromptProgressEvents.LLM_REQUEST, "nobody is listening")

    def test_emit_sends_to_the_current_sink_only(self):
        received = []
        with progress_sink(received.append):
            emit(PromptProgressEvents.LLM_REQUEST, "hello", iteration=1)
        emit(PromptProgressEvents.LLM_REQUEST, "after")
        self.assertEqual(received, [{"type": "llm_request", "message": "hello", "iteration": 1}])

    def test_a_failing_sink_never_fails_the_prompt(self):
        def sink(event):
            raise ValueError("broken sink")

        with progress_sink(sink), patch.object(progress, "logger") as logger:
            emit(PromptProgressEvents.LLM_REQUEST, "hello")
        logger.exception.assert_called_once()

    def test_wants_event_stream(self):
        factory = RequestFactory()
        self.assertTrue(wants_event_stream(factory.post("/", HTTP_ACCEPT="text/event-stream, application/json")))
        self.assertFalse(wants_event_stream(factory.post("/", HTTP_ACCEPT="application/json")))
        self.assertFalse(wants_event_stream(factory.post("/")))


class TestReceivers(TestCase):
    """Test that the prompt's signals become progress events."""

    def received(self, send) -> list[dict]:
        received: list[dict] = []
        with progress_sink(received.append):
            send()
        return received

    def test_receivers_are_connected(self):
        for signal, uid in (
            (chat_request, "smarter.apps.prompt.progress.chat_request"),
            (chat_plugin_called, "smarter.apps.prompt.progress.chat_plugin_called"),
        ):
            with self.subTest(uid=uid):
                self.assertIn(uid, [receiver[0][0] for receiver in signal.receivers])

    def test_chat_request(self):
        # called directly: the prompt app's other receivers of these signals need a real prompt.
        first = self.received(lambda: progress.handle_chat_request(sender=None, iteration=1))
        second = self.received(lambda: progress.handle_chat_request(sender=None, iteration=2))
        self.assertEqual(first, [{"type": "llm_request", "message": "Sending the prompt to the LLM", "iteration": 1}])
        self.assertEqual(second[0]["message"], "Sending the tool results to the LLM")

    def test_tool_calls_from_the_tool_call_loop(self):
        requested = self.received(lambda: llm_tool_requested.send(sender=process_tool_call, tool_call=TOOL_CALL))
        responded = self.received(
            lambda: llm_tool_responded.send(sender=process_tool_call, tool_call=TOOL_CALL, tool_response={})
        )
        self.assertEqual(
            requested,
            [
                {
                    "type": "tool_requested",
                    "message": "Calling tool get_current_weather",
                    "tool": "get_current_weather",
                    "arguments": '{"a": 1}',
                }
            ],
        )
        self.assertEqual(responded[0]["message"], "Tool get_current_weather responded")

    def test_tool_signals_of_built_in_functions_are_not_duplicated(self):
        received = self.received(
            lambda: (
                llm_tool_requested.send(sender=get_current_weather, tool_call=TOOL_CALL),
                llm_tool_responded.send(sender=get_current_weather, tool_call=TOOL_CALL, tool_response={}),
            )
        )
        self.assertEqual(received, [])

    def test_long_tool_arguments_are_truncated(self):
        tool_call = {"function": {"name": "f", "arguments": {"text": "x" * 1000}}}
        received = self.received(lambda: llm_tool_requested.send(sender=process_tool_call, tool_call=tool_call))
        self.assertEqual(len(received[0]["arguments"]), progress.MAX_ARGUMENTS_LENGTH + 3)

    def test_a_malformed_tool_call_has_no_name(self):
        received = self.received(lambda: llm_tool_requested.send(sender=process_tool_call, tool_call=None))
        self.assertEqual(received[0]["tool"], "")

    def test_plugin_called(self):
        plugin = MagicMock()
        plugin.name = "stackademy_sql"
        received = self.received(lambda: progress.handle_chat_plugin_called(sender=None, plugin=plugin))
        self.assertEqual(
            received[0],
            {"type": "plugin_called", "message": "Running plugin stackademy_sql", "plugin": "stackademy_sql"},
        )

    def test_mcp_server_tool_calls(self):
        mcpclient = MagicMock()
        mcpclient.name = "github"
        received = self.received(
            lambda: (
                mcpclient_tool_called.send(
                    sender=None, mcpclient=mcpclient, tool_name="search_code", arguments={"q": "smarter"}
                ),
                mcpclient_tool_responded.send(
                    sender=None, mcpclient=mcpclient, tool_name="search_code", is_error=False, characters=10
                ),
                mcpclient_tool_failed.send(sender=None, mcpclient=mcpclient, tool_name="search_code", error="down"),
            )
        )
        self.assertEqual(
            [event["type"] for event in received],
            ["mcp_tool_called", "mcp_tool_responded", "mcp_tool_failed"],
        )
        self.assertEqual(received[0]["message"], "Calling MCP server github: search_code")
        self.assertEqual(received[0]["arguments"], '{"q": "smarter"}')
        self.assertFalse(received[1]["is_error"])
        self.assertEqual(received[2]["error"], "down")


class TestPromptEventStream(TestCase):
    """Test the prompt api's streaming response."""

    @staticmethod
    def on_error(e: Exception) -> HttpResponse:
        return JsonResponse({"error": str(e)}, status=HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_streams_the_progress_then_the_result(self):
        def complete():
            emit(PromptProgressEvents.LLM_REQUEST, "Sending the prompt to the LLM")
            llm_tool_requested.send(sender=process_tool_call, tool_call=TOOL_CALL)
            return JsonResponse({"data": "done"}, status=HTTPStatus.CREATED)

        frames = collect(prompt_event_stream(complete, self.on_error))
        self.assertEqual(frames[0], "retry: 3000\n\n")
        self.assertEqual([event["type"] for event in events(frames, "progress")], ["llm_request", "tool_requested"])
        self.assertEqual(events(frames, "result"), [{"status": 201, "response": {"data": "done"}}])
        self.assertTrue(frames[-1].startswith("event: result"))

    def test_a_failed_prompt_is_its_error_response(self):
        def complete():
            raise RuntimeError("the LLM is down")

        frames = collect(prompt_event_stream(complete, self.on_error))
        self.assertEqual(events(frames, "result"), [{"status": 500, "response": {"error": "the LLM is down"}}])

    def test_a_response_that_is_not_json_is_its_text(self):
        frames = collect(prompt_event_stream(lambda: HttpResponse("plain"), self.on_error))
        self.assertEqual(events(frames, "result"), [{"status": 200, "response": {"error": "plain"}}])

    def test_keeps_an_idle_connection_alive(self):
        def complete():
            time.sleep(0.2)
            return JsonResponse({})

        with patch.object(progress, "KEEPALIVE_SECONDS", 0.05):
            frames = collect(prompt_event_stream(complete, self.on_error))
        self.assertIn(": keepalive\n\n", frames)

    def test_a_client_that_disconnects_does_not_stop_the_prompt(self):
        finished = []

        def complete():
            time.sleep(0.2)
            finished.append(True)
            return JsonResponse({})

        async def disconnect():
            stream = prompt_event_stream(complete, self.on_error)
            await stream.__anext__()  # retry
            await stream.__anext__()  # keepalive, while the prompt runs
            await stream.aclose()
            await asyncio.sleep(0.5)

        with patch.object(progress, "logger") as logger, patch.object(progress, "KEEPALIVE_SECONDS", 0.05):
            asyncio.run(disconnect())
        self.assertEqual(finished, [True])
        logger.info.assert_called_once()

    def test_the_response_is_an_uncached_event_stream(self):
        response = prompt_event_stream_response(lambda: JsonResponse({}), self.on_error)
        self.assertEqual(response["Content-Type"], "text/event-stream")
        self.assertEqual(response["Cache-Control"], "no-cache")
        self.assertEqual(response["X-Accel-Buffering"], "no")
        self.assertEqual(
            collect(response.streaming_content)[-1], 'event: result\ndata: {"status": 200, "response": {}}\n\n'
        )
