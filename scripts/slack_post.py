#!/usr/bin/env python3
"""Post a message, read from stdin, to a Slack channel.

Usage::

    echo "*Build #42 passed*" | python3 -I scripts/slack_post.py --channel smarter [--dry-run]

The workflows' Slack messages (test.yml, build.yml, deploy.yml) are written by their steps, or by
scripts/slack_test_report.py, in Slack's mrkdwn, and piped into this script, which is the one
place that talks to Slack. It posts with ``chat.postMessage`` and the bot token in
``SLACK_BOT_TOKEN``, which is read from the environment, never from an argument, and is never
printed. The bot must be a member of the channel, with the chat:write scope.

Without a token, e.g. in a pull request from a fork, or with an empty message, nothing is posted,
and the exit code is 0. ``--dry-run`` prints the message instead. A message that Slack refuses
exits with 1, so the workflows mark their Slack steps ``continue-on-error``: a Slack outage must
never fail a build or a deployment.
"""

import argparse
import json
import os
import sys
import urllib.request

SLACK_POST_MESSAGE_URL = "https://slack.com/api/chat.postMessage"


def post(channel: str, text: str, token: str) -> None:
    """
    Post a message to a Slack channel with ``chat.postMessage``.

    :param channel: A channel name, e.g. ``smarter``, or id.
    :param text: The message, in Slack's mrkdwn.
    :param token: The bot token.
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


def main(argv: list[str] | None = None) -> int:
    """Read the message from stdin, then print it (--dry-run) or post it.

    Returns the exit code.
    """
    parser = argparse.ArgumentParser(description=(__doc__ or "").splitlines()[0])
    parser.add_argument("--channel", required=True, help="A channel name, e.g. smarter, or id.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    text = sys.stdin.read().strip()
    if not text:
        print("slack_post.py: the message is empty, so nothing is posted")
        return 0
    if args.dry_run:
        print(text)
        return 0
    token = os.environ.get("SLACK_BOT_TOKEN", "")
    if not token:
        print("slack_post.py: SLACK_BOT_TOKEN is not set, so nothing is posted")
        return 0
    try:
        post(args.channel, text, token)
    except (OSError, RuntimeError, ValueError) as e:
        print(f"slack_post.py: {e}", file=sys.stderr)
        return 1
    print(f"slack_post.py: posted to {args.channel}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
