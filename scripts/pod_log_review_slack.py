#!/usr/bin/env python3
"""Tell a Slack channel what an unattended Claude Code review wrote to GitHub, or that all was well.

This is the last step of ``.github/workflows/podLogReview.yml`` before its cleanup.

Usage::

    python3 -E -s scripts/pod_log_review_slack.py <stream.jsonl> \\
        --channel smarter --title "Pod log review: prod" [--run-url URL] \\
        [--log-dir DIR] [--since 25h] [--dry-run]

It reads the run's ``claude -p --output-format stream-json --verbose`` output, and posts at most
one message, through ``slack_post.py``, the one place that talks to Slack, with the bot token in
``SLACK_BOT_TOKEN``. The bot must be a member of the channel. ``--dry-run`` prints the message
instead.

- **The run wrote to GitHub.** The message lists each call of the Smarter Project MCP server's
  write tools that succeeded (an issue opened, commented on or closed, a pull request proposed),
  with its link. What happened is taken from the tool's result, which the MCP server wrote after
  GitHub accepted the change, never from what Claude says it did.
- **It wrote nothing, and was healthy.** Claude Code finished without an error, and its final
  answer ends with the exact line ``Verdict: healthy`` (see
  :attr:`pod_log_review_stream.ReviewResult.healthy`). The message is a clean bill of health, whose facts
  (pods, restarts, release) come from the kubectl inventory in ``--log-dir``. The verdict is the
  only thing taken from Claude, and it chooses between fixed texts, so nothing that Claude or the
  logs wrote reaches Slack.
- **Anything else** posts nothing.

The token is read from the environment, never from an argument, and is never printed.

It uses only Python's standard library, which comes with every Python install, and
``slack_post.py``, the workflows' one module that talks to Slack:

- ``argparse`` reads the command line: the stream's path, ``--channel``, ``--title`` and the rest.
- ``os`` reads ``SLACK_BOT_TOKEN`` from the environment, and checks that the stream exists.
- ``re`` is regular expressions: :data:`GITHUB_URL` finds the link in a tool's result, and
  :func:`format_action` uses ``re.sub()`` to drop the tool's own wording from it.
- ``sys`` gives the command line's arguments, the exit code and the error stream (``sys.stderr``).
"""

import argparse
import os
import re
import sys

from pod_log_review_stream import (
    WRITE_TOOLS,
    JsonObject,
    PodInventory,
    content_blocks,
    events,
    final_result,
    tool_name,
)
from slack_post import post

DESCRIPTION = "Tell a Slack channel what an unattended Claude Code review wrote to GitHub, or that all was well."
"""The command line's description."""

ACTION_LABELS = {
    "create_issue": ":new: Opened",
    "comment_on_issue": ":speech_balloon: Commented on",
    "close_issue": ":white_check_mark: Closed",
    "create_pull_request": ":twisted_rightwards_arrows: Proposed",
}
"""How the message introduces each of the write tools, :data:`pod_log_review_stream.WRITE_TOOLS`."""

GITHUB_URL = re.compile(r"https://github\.com/[\w.-]+/[\w.-]+/(?:issues|pull)/\d+(?:#issuecomment-\d+)?")
"""A link to an issue, a pull request or a comment, as the MCP server's write tools return it."""

MAX_LINE = 200
"""The longest line, in characters, that the message shows for one action."""

MAX_ACTIONS = 40
"""The most actions the message lists; it counts the rest."""


def result_text(content: object) -> str:
    """
    Return the text of a ``tool_result`` block's content.

    :param content: The block's ``content``: a string, or a list of content blocks.
    :returns: The text, with the text of several blocks joined by newlines, or an empty string
        for any other shape.
    """
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        return "\n".join(str(block.get("text", "")) for block in content if isinstance(block, dict))
    return ""


def escape(text: str) -> str:
    """
    Escape text for Slack's mrkdwn, so that it shows as written rather than as a link or a mention.

    :param text: The text.
    :returns: The text with ``&``, ``<`` and ``>`` replaced by their entities.
    """
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def actions(path: str) -> list[str]:
    """
    Return one line of Slack mrkdwn for each GitHub write that succeeded, in the order they ran.

    A write succeeded when its ``tool_result`` is not an error and holds a GitHub link: the MCP
    server returns one only after GitHub accepted the change.

    :param path: The stream-json output of the run.
    :returns: The lines, from :func:`format_action`, or an empty list if nothing was written.
    """
    calls: dict[str, str] = {}
    lines: list[str] = []
    for event in events(path):
        for block in content_blocks(event):
            if block.get("type") == "tool_use":
                name = tool_name(str(block.get("name", "")))
                if name in WRITE_TOOLS:
                    calls[str(block.get("id"))] = name
            elif block.get("type") == "tool_result" and str(block.get("tool_use_id")) in calls:
                name = calls.pop(str(block.get("tool_use_id")))
                line = format_action(name, block)
                if line:
                    lines.append(line)
    return lines


def format_action(name: str, block: JsonObject) -> str | None:
    """
    Return one write as a line of Slack mrkdwn: what was done, and a link to it.

    :param name: The tool's name, one of :data:`pod_log_review_stream.WRITE_TOOLS`.
    :param block: The tool's ``tool_result`` block. Its text is e.g.
        ``Opened issue #42 in smarter-sh/smarter by x: title``, then the link on the next line.
    :returns: The line, e.g. ``:new: Opened issue #42 in smarter-sh/smarter: title <url|view>``, or
        None if the write failed or its result has no GitHub link.
    """
    text = result_text(block.get("content"))
    link = GITHUB_URL.search(text)
    if block.get("is_error") or not link:
        return None
    first = text.strip().splitlines()[0]
    # the tool's own verb is replaced by the label's, and its author dropped.
    first = re.sub(r"^(Opened( draft)?|Commented on|Closed)\s+", "", first)
    first = re.sub(r" by [\w-]+(?=[:,.])", "", first)
    if len(first) > MAX_LINE:
        first = first[: MAX_LINE - 3] + "..."
    return f"{ACTION_LABELS[name]} {escape(first)} <{link.group(0)}|view>"


def footer(run_url: str) -> str:
    """
    Return the message's last line: a link to the workflow run, and who wrote the message.

    :param run_url: The workflow run's url, or an empty string for none.
    """
    return f"<{run_url}|Workflow run> · written by Claude Code" if run_url else "written by Claude Code"


def actions_message(title: str, lines: list[str], run_url: str) -> str:
    """
    Return the message of a run that wrote to GitHub: a heading, one line per write, and a footer.

    :param title: The heading, e.g. ``Pod log review of ubc.smarter.sh``.
    :param lines: The writes, from :func:`actions`. Only the first :data:`MAX_ACTIONS` are listed.
    :param run_url: The workflow run's url, or an empty string.
    :returns: The message, in Slack mrkdwn.
    """
    shown = lines[:MAX_ACTIONS]
    more = [f"…and {len(lines) - len(shown)} more"] if len(lines) > len(shown) else []
    return "\n".join([f"*{escape(title)}*", *shown, *more, footer(run_url)])


def clean_bill_of_health(title: str, inventory: PodInventory, since: str, run_url: str) -> str:
    """
    Return the message of a run that found nothing to fix.

    Each fact that the inventory lacks is left out, rather than shown as unknown.

    :param title: The heading, e.g. ``Pod log review of ubc.smarter.sh``.
    :param inventory: The reviewed pods, from :meth:`pod_log_review_stream.PodInventory.read`.
    :param since: How far back each log reaches, e.g. ``25h``, or an empty string for each
        container's whole log.
    :param run_url: The workflow run's url, or an empty string.
    :returns: The message, in Slack mrkdwn.
    """
    span = f"the last {escape(since)} of logs" if since else "every log"
    lines = [
        f"*{escape(title)}*",
        f":sunny: *Clean bill of health!* Claude read {span} and found nothing that needs fixing.",
    ]
    if inventory.pods:
        total = sum(inventory.pods.values())
        each = ", ".join(f"{escape(name)} {count}" for name, count in inventory.pods.items())
        lines.append(f":white_check_mark: {total} pod(s) up and running ({each})")
    if inventory.restarts == 0:
        lines.append(":muscle: Zero restarts")
    elif inventory.restarts:
        lines.append(f":repeat: {inventory.restarts} restart(s), and Claude judged them harmless")
    if inventory.releases:
        lines.append(f":package: Release {', '.join(escape(tag) for tag in inventory.releases)}")
    lines.append(":coffee: No new issues, nothing to close. Enjoy your day!")
    lines.append(footer(run_url))
    return "\n".join(lines)


def message(stream: str, title: str, run_url: str, log_dir: str, since: str) -> str | None:
    """
    Return the run's message: its GitHub writes, or a clean bill of health, or None.

    :param stream: The run's stream-json output.
    :param title: The message's heading.
    :param run_url: The workflow run's url, or an empty string.
    :param log_dir: The folder of ``download-logs.sh``, for a clean bill of health.
    :param since: How far back each log reaches, e.g. ``25h``, or an empty string.
    :returns: The message, in Slack mrkdwn, or None if the run wrote nothing and wasn't healthy.
    """
    lines = actions(stream)
    if lines:
        return actions_message(title, lines, run_url)
    result = final_result(stream)
    if result is not None and result.healthy:
        return clean_bill_of_health(title, PodInventory.read(log_dir), since, run_url)
    return None


def main() -> int:
    """
    Post the run's message, if it has one.

    :returns: 0 if the message was posted, or there was nothing to post, or no token; 1 if the
        stream doesn't exist or Slack refused the message.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("stream", help="the run's stream-json output")
    parser.add_argument("--channel", required=True, help="a channel's name, e.g. smarter, or its id")
    parser.add_argument("--title", required=True, help="the message's heading")
    parser.add_argument("--run-url", default="", help="the workflow run's url")
    parser.add_argument("--log-dir", default="", help="the folder of download-logs.sh, for a clean bill of health")
    parser.add_argument("--since", default="", help="how far back each log reaches, e.g. 25h")
    parser.add_argument("--dry-run", action="store_true", help="print the message instead of posting it")
    args = parser.parse_args()
    if not os.path.exists(args.stream):
        print(f"pod_log_review_slack.py: {args.stream} does not exist", file=sys.stderr)
        return 1
    text = message(args.stream, args.title, args.run_url, args.log_dir, args.since)
    if text is None:
        print(
            "pod_log_review_slack.py: nothing was written to GitHub, and the run was not healthy, so nothing is posted"
        )
        return 0
    if args.dry_run:
        print(text)
        return 0
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        print("pod_log_review_slack.py: SLACK_BOT_TOKEN is not set, so nothing is posted")
        return 0
    try:
        post(args.channel, text, token)
    except (OSError, RuntimeError, ValueError) as e:
        print(f"pod_log_review_slack.py: {e}", file=sys.stderr)
        return 1
    print(f"pod_log_review_slack.py: posted to {args.channel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
