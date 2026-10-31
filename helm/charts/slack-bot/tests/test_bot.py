"""
Tests of the Smarter Slack bot, files/bot.py.

They need only the standard library: the LLMClient's api is faked, and Slack Bolt is
replaced by a fake app. Run them from the repository's root:

    python -m unittest discover -s helm/charts/slack-bot/tests
"""

import importlib.util
import io
import json
import sys
import unittest
from pathlib import Path
from unittest import mock

BOT_PATH = Path(__file__).resolve().parent.parent / "files" / "bot.py"
spec = importlib.util.spec_from_file_location("smarter_slack_bot", BOT_PATH)
bot = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bot)

AGENT_URL = "https://agent.example.com/"


def prompt_response(*messages):
    """A response of the LLMClient's prompt api, with these messages."""
    return {"data": {"messages": list(messages)}}


class FakeAgentApi:
    """Answers AgentClient._post(): config/ with a new session key, prompt/ with the queued responses."""

    def __init__(self, *responses):
        self.responses = list(responses)
        self.calls = []
        self.sessions = 0

    def __call__(self, path, body):
        self.calls.append((path, json.loads(json.dumps(body))))
        if path == "config/":
            self.sessions += 1
            return {"data": {"session_key": f"session-{self.sessions}"}}
        return self.responses.pop(0)


class FakeApp:
    """A stand-in for Slack Bolt's App, which records the event listeners."""

    def __init__(self):
        self.listeners = {}

    def event(self, name):
        def decorator(func):
            self.listeners[name] = func
            return func

        return decorator


class TestToSlack(unittest.TestCase):
    """To_slack() converts the Markdown that Slack would show literally."""

    def test_link(self):
        self.assertEqual(
            bot.to_slack("See [the docs](https://docs.smarter.sh/en/latest/)."),
            "See <https://docs.smarter.sh/en/latest/|the docs>.",
        )

    def test_bold(self):
        self.assertEqual(bot.to_slack("a **bold** word"), "a *bold* word")

    def test_heading(self):
        self.assertEqual(bot.to_slack("## Install\ntext"), "*Install*\ntext")

    def test_code_is_unchanged(self):
        text = "```yaml\nkind: LLMClient\n```\n- `smarter apply`"
        self.assertEqual(bot.to_slack(text), text)

    def test_image_becomes_a_link(self):
        self.assertEqual(
            bot.to_slack("![Network policies](https://cdn.example.com/np.png)"),
            "<https://cdn.example.com/np.png|Network policies>",
        )

    def test_image_without_alt_text(self):
        self.assertEqual(bot.to_slack("![](https://cdn.example.com/np.png)"), "<https://cdn.example.com/np.png|image>")


class TestQuestionText(unittest.TestCase):
    """Question_text() removes mentions."""

    def test_mention(self):
        self.assertEqual(bot.question_text("<@U0BOT123> what is a Plugin?"), "what is a Plugin?")

    def test_empty(self):
        self.assertEqual(bot.question_text(None), "")
        self.assertEqual(bot.question_text("<@U0BOT123>"), "")


class TestAgentClient(unittest.TestCase):
    """AgentClient keeps one chat session per thread and returns the final answer."""

    def client(self, api, **kwargs):
        agent = bot.AgentClient(AGENT_URL, **kwargs)
        agent._post = api  # pylint: disable=protected-access
        return agent

    def test_url_has_no_trailing_slash(self):
        self.assertEqual(bot.AgentClient(AGENT_URL).url, "https://agent.example.com")

    def test_final_answer_after_tool_calls(self):
        api = FakeAgentApi(
            prompt_response(
                {"role": "smarter", "content": "Tool presented"},
                {"role": "assistant", "content": None, "tool_calls": [{"id": "1"}]},
                {"role": "tool", "content": "{}"},
                {"role": "assistant", "content": "A Plugin connects an LLM to data."},
                {"role": "smarter", "content": "charges"},
            )
        )
        agent = self.client(api)
        self.assertEqual(agent.ask("C1:1", "What is a Plugin?"), "A Plugin connects an LLM to data.")
        self.assertEqual(api.calls[0], ("config/", {}))
        self.assertEqual(
            api.calls[1],
            ("prompt/", {"session_key": "session-1", "messages": [{"role": "user", "content": "What is a Plugin?"}]}),
        )

    def test_thread_keeps_only_questions_and_answers(self):
        api = FakeAgentApi(
            prompt_response({"role": "tool", "content": "{}"}, {"role": "assistant", "content": "one"}),
            prompt_response({"role": "assistant", "content": "two"}),
        )
        agent = self.client(api)
        agent.ask("C1:1", "q1")
        self.assertEqual(agent.ask("C1:1", "q2"), "two")
        self.assertEqual(api.sessions, 1)
        self.assertEqual(
            api.calls[-1][1]["messages"],
            [
                {"role": "user", "content": "q1"},
                {"role": "assistant", "content": "one"},
                {"role": "user", "content": "q2"},
            ],
        )

    def test_each_thread_has_its_own_session(self):
        api = FakeAgentApi(prompt_response({"role": "assistant", "content": "a"}), prompt_response())
        agent = self.client(api)
        agent.ask("C1:1", "q")
        self.assertEqual(agent.ask("C1:2", "q"), bot.NO_ANSWER)
        self.assertEqual(api.sessions, 2)
        self.assertEqual(api.calls[-1][1]["session_key"], "session-2")

    def test_least_recently_used_session_is_forgotten(self):
        api = FakeAgentApi(*[prompt_response({"role": "assistant", "content": "a"}) for _ in range(4)])
        agent = self.client(api, max_sessions=2)
        agent.ask("t1", "q")
        agent.ask("t2", "q")
        agent.ask("t1", "q")  # t1 is now the most recently used
        agent.ask("t3", "q")
        self.assertEqual(list(agent._sessions), ["t1", "t3"])  # pylint: disable=protected-access

    def test_reply_converts_to_slack(self):
        api = FakeAgentApi(prompt_response({"role": "assistant", "content": "**yes**, [docs](https://x.example/)"}))
        self.assertEqual(self.client(api).reply("t", "<@U1> ok?"), "*yes*, <https://x.example/|docs>")

    def test_reply_to_an_empty_mention(self):
        api = FakeAgentApi()
        self.assertEqual(self.client(api).reply("t", "<@U1>"), bot.EMPTY_QUESTION)
        self.assertEqual(api.calls, [])

    def test_reset_starts_a_new_conversation(self):
        api = FakeAgentApi(
            prompt_response({"role": "assistant", "content": "one"}),
            prompt_response({"role": "assistant", "content": "two"}),
        )
        agent = self.client(api)
        agent.ask("t", "q1")
        for word in ("<@U1> reset", "New conversation.", "start over!"):
            self.assertEqual(agent.reply("t", word), bot.NEW_CONVERSATION)
        self.assertEqual(agent.ask("t", "q2"), "two")
        self.assertEqual(api.sessions, 2)
        self.assertEqual(api.calls[-1][1]["messages"], [{"role": "user", "content": "q2"}])

    def test_reset_word_inside_a_question_is_a_question(self):
        api = FakeAgentApi(prompt_response({"role": "assistant", "content": "a"}))
        self.assertEqual(self.client(api).reply("t", "how do I reset my password?"), "a")

    def test_forget_an_unknown_thread(self):
        self.client(FakeAgentApi()).forget("unknown")

    def test_reply_when_the_agent_fails(self):
        agent = bot.AgentClient(AGENT_URL)
        with mock.patch.object(agent, "_post", side_effect=OSError("down")), self.assertLogs(bot.logger, "ERROR"):
            self.assertEqual(agent.reply("t", "hello"), bot.AGENT_ERROR)

    def test_post(self):
        response = mock.MagicMock()
        response.__enter__.return_value.read.return_value = b'{"data": {"session_key": "k"}}'
        with mock.patch.object(bot.urllib.request, "urlopen", return_value=response) as urlopen:
            result = bot.AgentClient(AGENT_URL, timeout=7)._post("config/", {})  # pylint: disable=protected-access
        self.assertEqual(result, {"data": {"session_key": "k"}})
        request = urlopen.call_args.args[0]
        self.assertEqual(request.full_url, "https://agent.example.com/config/")
        self.assertEqual(request.get_method(), "POST")
        self.assertEqual(request.data, b"{}")
        self.assertEqual(urlopen.call_args.kwargs["timeout"], 7)


class TestListeners(unittest.TestCase):
    """Register() answers mentions in their thread, and direct messages in the conversation."""

    def setUp(self):
        self.app = FakeApp()
        self.agent = mock.Mock(spec=bot.AgentClient)
        self.agent.reply.return_value = "answer"
        bot.register(self.app, self.agent)
        self.say = mock.Mock()

    def test_mention_starts_a_thread(self):
        self.app.listeners["app_mention"]({"channel": "C1", "ts": "1.0", "text": "<@U1> hi"}, self.say)
        self.agent.reply.assert_called_once_with("C1:1.0", "<@U1> hi")
        self.say.assert_called_once_with(text="answer", thread_ts="1.0")

    def test_mention_in_a_thread(self):
        event = {"channel": "C1", "ts": "2.0", "thread_ts": "1.0", "text": "<@U1> more"}
        self.app.listeners["app_mention"](event, self.say)
        self.agent.reply.assert_called_once_with("C1:1.0", "<@U1> more")
        self.say.assert_called_once_with(text="answer", thread_ts="1.0")

    def test_direct_message(self):
        self.app.listeners["message"]({"channel_type": "im", "channel": "D1", "text": "hi"}, self.say)
        self.agent.reply.assert_called_once_with("D1", "hi")
        self.say.assert_called_once_with(text="answer")

    def test_direct_message_in_a_thread(self):
        event = {"channel_type": "im", "channel": "D1", "ts": "2.0", "thread_ts": "1.0", "text": "more"}
        self.app.listeners["message"](event, self.say)
        self.agent.reply.assert_called_once_with("D1:1.0", "more")
        self.say.assert_called_once_with(text="answer", thread_ts="1.0")

    def test_ignored_messages(self):
        for event in (
            {"channel_type": "channel", "channel": "C1", "text": "hi"},
            {"channel_type": "im", "channel": "D1", "text": "hi", "bot_id": "B1"},
            {"channel_type": "im", "channel": "D1", "text": "hi", "subtype": "message_changed"},
        ):
            self.app.listeners["message"](event, self.say)
        self.agent.reply.assert_not_called()
        self.say.assert_not_called()


class TestMain(unittest.TestCase):
    """Main() wires the environment, the agent and Socket Mode together."""

    def test_main(self):
        slack_bolt = mock.MagicMock()
        socket_mode = mock.MagicMock()
        modules = {
            "slack_bolt": slack_bolt,
            "slack_bolt.adapter": mock.MagicMock(),
            "slack_bolt.adapter.socket_mode": socket_mode,
        }
        environ = {
            "SMARTER_SLACK_BOT_AGENT_URL": AGENT_URL,
            "SMARTER_SLACK_BOT_TOKEN": "xoxb-test",
            "SMARTER_SLACK_APP_TOKEN": "xapp-test",
        }
        with (
            mock.patch.dict(sys.modules, modules),
            mock.patch.dict(bot.os.environ, environ),
            mock.patch.object(bot.logging, "basicConfig"),
            mock.patch.object(bot, "register") as register,
            mock.patch("sys.stderr", io.StringIO()),
        ):
            bot.main()
        slack_bolt.App.assert_called_once_with(token="xoxb-test")
        agent = register.call_args.args[1]
        self.assertEqual((agent.url, agent.timeout), ("https://agent.example.com", 240.0))
        socket_mode.SocketModeHandler.assert_called_once_with(slack_bolt.App.return_value, "xapp-test")
        socket_mode.SocketModeHandler.return_value.start.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
