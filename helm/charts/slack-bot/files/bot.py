"""
Smarter Slack bot.

Answers questions in a Slack workspace with a deployed Smarter LLMClient, such as
smarter_developer. It listens with Slack's Socket Mode, so it needs no public url,
and it talks to the LLMClient with the Smarter Chat api of the LLMClient's own host:

- ``POST <agent-url>/config/`` starts a chat session and returns its ``session_key``.
- ``POST <agent-url>/prompt/`` sends the thread, and the LLMClient's answer is the
  last ``assistant`` message, with content, of the response's ``data.messages``.

Each Slack thread (or direct-message channel) is one chat session. Sessions are kept
in memory, so a restart starts every conversation again.

Environment:

- ``SMARTER_SLACK_BOT_TOKEN``: the Slack app's bot token, ``xoxb-...``.
- ``SMARTER_SLACK_APP_TOKEN``: the Slack app's app-level token, ``xapp-...``, with
  ``connections:write``.
- ``SMARTER_SLACK_BOT_AGENT_URL``: the LLMClient's url, e.g.
  ``https://smarter-developer.<account-number>.api.<domain>/``.
- ``SMARTER_SLACK_BOT_TIMEOUT``: seconds to wait for an answer, 240 by default.

Only the Slack Bolt package is needed beyond the standard library. It is imported in
:func:`main`, so that the rest of this module can be tested without it.
"""

import json
import logging
import os
import re
import threading
import urllib.request
from collections import OrderedDict

logger = logging.getLogger("smarter.slack_bot")
logger_prefix = "smarter.slack_bot"

NO_ANSWER = "Sorry, I have no answer to that."
AGENT_ERROR = "Sorry, I couldn't reach the Smarter agent. Please try again in a minute."
EMPTY_QUESTION = "Hi! Ask me a question about Smarter, and I'll answer in this thread."
NEW_CONVERSATION = "OK, let's start a new conversation. What would you like to know?"

# A message that is only one of these words starts a new conversation in its thread.
RESET_WORDS = frozenset({"new", "reset", "start over", "new conversation"})


def to_slack(text: str) -> str:
    """
    Convert the Markdown of an LLM's answer to Slack's mrkdwn.

    Converts images, links, bold text and headings, which Slack would otherwise show literally.
    An image becomes a link to it. Code blocks, inline code and bullet lists are the same in
    both, and are left as they are.

    :param text: Markdown.
    :returns: Slack mrkdwn.
    """
    text = re.sub(r"!\[([^\]]*)\]\((https?://[^)\s]+)\)", lambda m: f"<{m[2]}|{m[1] or 'image'}>", text)
    text = re.sub(r"\[([^\]]+)\]\((https?://[^)\s]+)\)", r"<\2|\1>", text)
    text = re.sub(r"\*\*(.+?)\*\*", r"*\1*", text)
    return re.sub(r"(?m)^#{1,6}\s+(.+)$", r"*\1*", text)


def question_text(text: str) -> str:
    """
    Remove Slack's user mentions, such as the bot's own ``<@U0123>``, from a message.

    :param text: The text of a Slack message.
    :returns: The question.
    """
    return re.sub(r"<@[A-Z0-9]+>", "", text or "").strip()


class AgentClient:
    """
    A client of a deployed Smarter LLMClient's chat api, with one chat session per Slack thread.

    :param url: The LLMClient's url.
    :param timeout: Seconds to wait for an answer.
    :param max_sessions: The most chat sessions to keep. The least recently used is forgotten first.
    """

    def __init__(self, url: str, timeout: float = 240, max_sessions: int = 500) -> None:
        self.url = url.rstrip("/")
        self.timeout = timeout
        self.max_sessions = max_sessions
        self._sessions: OrderedDict[str, dict] = OrderedDict()
        self._lock = threading.Lock()

    def _post(self, path: str, body: dict) -> dict:
        """
        POST json to the LLMClient.

        :param path: The path, ``config/`` or ``prompt/``.
        :param body: The request's body.
        :returns: The response's json.
        """
        request = urllib.request.Request(
            f"{self.url}/{path}",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json", "Accept": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(request, timeout=self.timeout) as response:  # nosec B310 - an https url from config
            return json.loads(response.read().decode("utf-8"))

    def _session(self, thread_id: str) -> dict:
        """
        A Slack thread's chat session, started on the LLMClient when the thread is new.

        :param thread_id: The Slack thread's id.
        :returns: The session: its ``session_key`` and ``messages``.
        """
        with self._lock:
            session = self._sessions.get(thread_id)
            if session is not None:
                self._sessions.move_to_end(thread_id)
                return session
        config = self._post("config/", {})["data"]
        session = {"session_key": config["session_key"], "messages": []}
        with self._lock:
            self._sessions[thread_id] = session
            while len(self._sessions) > self.max_sessions:
                self._sessions.popitem(last=False)
        return session

    def ask(self, thread_id: str, text: str) -> str:
        """
        Ask the LLMClient a question in a Slack thread's chat session.

        Only the user's questions and the LLMClient's final answers are kept in the thread.
        The tool calls in between are the platform's, and it records them in the session.

        :param thread_id: The Slack thread's id.
        :param text: The question.
        :returns: The answer, in Markdown.
        """
        session = self._session(thread_id)
        messages = [*session["messages"], {"role": "user", "content": text}]
        response = self._post("prompt/", {"session_key": session["session_key"], "messages": messages})
        answers = [
            m["content"]
            for m in response.get("data", {}).get("messages", [])
            if m.get("role") == "assistant" and isinstance(m.get("content"), str) and m["content"].strip()
        ]
        answer = answers[-1] if answers else NO_ANSWER
        session["messages"] = [*messages, {"role": "assistant", "content": answer}]
        return answer

    def forget(self, thread_id: str) -> None:
        """
        Forget a Slack thread's chat session, so that its next question starts a new one.

        :param thread_id: The Slack thread's id.
        """
        with self._lock:
            self._sessions.pop(thread_id, None)

    def reply(self, thread_id: str, text: str) -> str:
        """
        The bot's reply to a Slack message: the LLMClient's answer, in Slack mrkdwn.

        A message that is only one of :data:`RESET_WORDS` starts a new conversation instead.

        :param thread_id: The Slack thread's id.
        :param text: The Slack message's text.
        :returns: The reply. Errors are logged, and answered with an apology.
        """
        question = question_text(text)
        if not question:
            return EMPTY_QUESTION
        if question.lower().strip(" .!") in RESET_WORDS:
            self.forget(thread_id)
            return NEW_CONVERSATION
        try:
            return to_slack(self.ask(thread_id, question))
        except Exception:  # pylint: disable=broad-exception-caught
            logger.exception("%s.reply() the agent at %s did not answer", logger_prefix, self.url)
            return AGENT_ERROR


def register(app, agent: AgentClient) -> None:
    """
    Register the bot's Slack event listeners.

    - ``app_mention``: answers in the thread of the message that mentions the bot. Each
      channel thread is one conversation.
    - ``message`` in a direct message: answers in the conversation, where the messages outside
      threads are one conversation, or in the message's thread, which is a conversation of its own.

    :param app: The Slack Bolt ``App``.
    :param agent: The LLMClient's client.
    """

    @app.event("app_mention")
    def on_mention(event, say):
        thread = event.get("thread_ts") or event["ts"]
        say(text=agent.reply(f"{event['channel']}:{thread}", event.get("text", "")), thread_ts=thread)

    @app.event("message")
    def on_message(event, say):
        if event.get("channel_type") != "im" or event.get("bot_id") or event.get("subtype"):
            return
        thread = event.get("thread_ts")
        if thread:
            say(text=agent.reply(f"{event['channel']}:{thread}", event.get("text", "")), thread_ts=thread)
        else:
            say(text=agent.reply(event["channel"], event.get("text", "")))


def main() -> None:
    """Run the bot with Slack's Socket Mode until the process is stopped."""
    # pylint: disable=import-outside-toplevel
    from slack_bolt import App
    from slack_bolt.adapter.socket_mode import SocketModeHandler

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    agent = AgentClient(
        os.environ["SMARTER_SLACK_BOT_AGENT_URL"],
        timeout=float(os.environ.get("SMARTER_SLACK_BOT_TIMEOUT", "240")),
    )
    app = App(token=os.environ["SMARTER_SLACK_BOT_TOKEN"])
    register(app, agent)
    logger.info("%s.main() answering with %s", logger_prefix, agent.url)
    SocketModeHandler(app, os.environ["SMARTER_SLACK_APP_TOKEN"]).start()


if __name__ == "__main__":
    main()
