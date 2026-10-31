#!/usr/bin/env python3
"""Post what an unattended Claude Code run wrote to GitHub, as one Slack message.

Usage::

    python3 -I skills/smarter-pod-log-review/scripts/slack-notify.py <stream.jsonl> \\
        --channel smarter --title "Pod log review: prod" [--run-url URL] [--dry-run]

It reads the run's ``claude -p --output-format stream-json --verbose`` output, and finds each call
of the Smarter Project MCP server's tools that write, ``create_issue``, ``comment_on_issue``,
``close_issue`` and ``create_pull_request``, that succeeded. It takes what happened from the tool's
result, which the MCP server wrote after GitHub accepted the change, never from what Claude says it
did. It posts one message that lists them, with their links, to the Slack channel, with
``chat.postMessage`` and the bot token in ``SLACK_BOT_TOKEN``. The bot must be a member of the
channel. A run that wrote nothing posts nothing. ``--dry-run`` prints the message instead.

The token is read from the environment, never from an argument, and is never printed.
"""

import argparse
import json
import os
import re
import sys
import urllib.request

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"
WRITE_TOOLS = {
    "create_issue": ":new: Opened",
    "comment_on_issue": ":speech_balloon: Commented on",
    "close_issue": ":white_check_mark: Closed",
    "create_pull_request": ":twisted_rightwards_arrows: Proposed",
}
"""The MCP server's tools that write to GitHub, and how the message introduces each."""
URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/(?:issues|pull)/\d+(?:#issuecomment-\d+)?")
MAX_LINE = 200
MAX_ACTIONS = 40


def tool_name(name: str) -> str:
    """Return a tool's name without its MCP prefix, e.g. ``create_issue`` for ``mcp__smarter-project__create_issue``."""
    return name.rsplit("__", 1)[-1]


def result_text(content) -> str:
    """Return a tool result's text, from a string or a list of content blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(block.get("text", "") for block in content if isinstance(block, dict))
    return ""


def escape(text: str) -> str:
    """Escape text for Slack's mrkdwn."""
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def actions(path: str) -> list[str]:
    """
    Return one line of Slack mrkdwn for each write tool call that succeeded, in the order they ran.

    :param path: The stream-json output of the run.
    """
    calls: dict[str, str] = {}
    lines: list[str] = []
    with open(path, encoding="utf-8") as stream:
        for raw in stream:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            turn = event.get("message") if isinstance(event, dict) else None
            content = turn.get("content") if isinstance(turn, dict) else None
            if not isinstance(content, list):
                continue
            for block in content:
                if not isinstance(block, dict):
                    continue
                if block.get("type") == "tool_use":
                    name = tool_name(str(block.get("name", "")))
                    if name in WRITE_TOOLS:
                        calls[str(block.get("id"))] = name
                elif block.get("type") == "tool_result" and str(block.get("tool_use_id")) in calls:
                    name = calls.pop(str(block.get("tool_use_id")))
                    text = result_text(block.get("content"))
                    if block.get("is_error") or not URL.search(text):
                        continue
                    lines.append(format_action(name, text))
    return lines


def format_action(name: str, text: str) -> str:
    """
    Return one action as a line of Slack mrkdwn: what was done, and a link to it.

    :param name: The tool's name.
    :param text: The tool's result, e.g. ``Opened issue #42 in smarter-sh/smarter by x: title\\nurl``.
    """
    first = text.strip().splitlines()[0]
    # the tool's own verb is replaced by the message's; the link is the issue or pull request.
    first = re.sub(r"^(Opened( draft)?|Commented on|Closed)\s+", "", first)
    first = re.sub(r" by [\w-]+(?=[:,.])", "", first)
    if len(first) > MAX_LINE:
        first = first[: MAX_LINE - 3] + "..."
    url = URL.search(text).group(0)
    return f"{WRITE_TOOLS[name]} {escape(first)} <{url}|view>"


def message(title: str, lines: list[str], run_url: str) -> str:
    """Return the Slack message: a heading, one line per action, and a link to the run."""
    shown = lines[:MAX_ACTIONS]
    more = f"\n…and {len(lines) - len(shown)} more" if len(lines) > len(shown) else ""
    footer = f"\n<{run_url}|Workflow run> · written by Claude Code" if run_url else "\nwritten by Claude Code"
    return f"*{escape(title)}*\n" + "\n".join(shown) + more + footer


def post(channel: str, text: str, token: str) -> None:
    """
    Post a message to a Slack channel with ``chat.postMessage``.

    :raises RuntimeError: If Slack refused it, e.g. ``not_in_channel``.
    """
    body = json.dumps({"channel": channel, "text": text, "unfurl_links": False, "unfurl_media": False}).encode()
    request = urllib.request.Request(  # nosec B310: a fixed https url
        SLACK_POST_MESSAGE_URL,
        data=body,
        headers={"Content-Type": "application/json; charset=utf-8", "Authorization": f"Bearer {token}"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:  # nosec B310
        answer = json.loads(response.read().decode())
    if not answer.get("ok"):
        raise RuntimeError(f"Slack refused the message: {answer.get('error', 'unknown error')}")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("stream")
    parser.add_argument("--channel", required=True, help="A channel name, e.g. smarter, or id.")
    parser.add_argument("--title", required=True)
    parser.add_argument("--run-url", default="")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not os.path.exists(args.stream):
        print(f"slack-notify.py: {args.stream} does not exist", file=sys.stderr)
        return 1
    lines = actions(args.stream)
    if not lines:
        print("slack-notify.py: nothing was written to GitHub, so nothing is posted")
        return 0
    text = message(args.title, lines, args.run_url)
    if args.dry_run:
        print(text)
        return 0
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        print("slack-notify.py: SLACK_BOT_TOKEN is not set, so nothing is posted")
        return 0
    try:
        post(args.channel, text, token)
    except (OSError, RuntimeError, ValueError) as e:
        print(f"slack-notify.py: {e}", file=sys.stderr)
        return 1
    print(f"slack-notify.py: posted {len(lines)} action(s) to {args.channel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
