#!/usr/bin/env python3
"""Run the daily pod log review with Claude Code, and put its summary on the workflow run's page.

This is the core of ``.github/workflows/podLogReview.yml``. The steps before it download and
redact the pods' logs, remove the cluster credentials, and configure the Smarter Project MCP
server; the step after it posts to Slack with ``pod_log_review_slack.py``.

Usage::

    python3 -E -s scripts/pod_log_review.py run
    python3 -E -s scripts/pod_log_review.py summarize

Both commands take their settings from the workflow's environment (see :class:`Settings`), and
share one file, ``$RUNNER_TEMP/claude/stream.jsonl``: Claude Code's ``stream-json`` output, which
``run`` writes and ``summarize`` and ``pod_log_review_slack.py`` read.

``run`` does this, in order:

1. Picks exactly one Anthropic credential: ``CLAUDE_CODE_OAUTH_TOKEN`` if it is set, else
   ``ANTHROPIC_API_KEY``. With neither, it fails.
2. Writes the prompt: the run's parameters (environment, log folder, release, limits, mode).
   Claude's instructions are in ``.github/prompts/pod-log-review.md``, which the prompt points to.
3. Runs ``claude -p`` with an environment that holds no AWS, Kubernetes or GitHub credential, and
   with the permissions of ``.github/prompts/pod-log-review.settings.json``.
4. Decides from the stream how it went:

   - it finished without an error: done, exit 0;
   - it failed on a transient API error (429 or 5xx), or died without finishing, *and* it never
     called a tool that writes to GitHub: wait two minutes and run it once more. A run that wrote
     is never repeated, because the second run would write the same issues again;
   - anything else (the budget, the turn limit, a second failure): exit 1.

``summarize`` appends Claude's final answer to ``$GITHUB_STEP_SUMMARY``, the run's page, and fails
if the run ended in an error. The workflow's logs are public and the stream holds the pod logs,
which anyone can write into, so neither command prints anything from the stream but Claude's final
answer, which follows the prompt's rules for public writing, and an API error's own message.

It uses only Python's standard library, which comes with every Python install:

- ``argparse`` reads the command line: here, ``run`` or ``summarize``.
- ``os`` reads the environment variables (``os.environ``) and joins paths (``os.path.join``).
- ``subprocess`` starts another program, here ``claude``, with an argument list and an
  environment of our choosing, waits for it, and returns its exit status. No shell is involved,
  so no argument is ever interpreted as shell syntax.
- ``time.sleep()`` waits before the retry.
- ``dataclasses.dataclass`` writes a class's ``__init__`` from its annotated fields, as in
  :class:`Settings`; ``frozen=True`` makes its instances read-only.
- ``datetime`` gives today's date, in UTC, for the prompt.
- ``sys`` gives the exit code.
"""

import argparse
import os
import subprocess  # nosec B404: runs the claude cli, with a fixed argument list
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

from pod_log_redact import REPORT_NAME, read_report
from pod_log_review_stream import (
    PodInventory,
    ReviewResult,
    final_result,
    write_attempts,
)

DESCRIPTION = "Run the daily pod log review with Claude Code, and put its summary on the workflow run's page."
"""The command line's description."""

ATTEMPTS = 2
"""How many times ``run`` starts Claude Code: the first run, and one retry when it is safe."""

RETRY_DELAY_SECONDS = 120
"""How long to wait before the retry, for an overloaded or rate-limited API to recover."""

SCRUBBED_ENV = (
    "AWS_ACCESS_KEY_ID",
    "AWS_SECRET_ACCESS_KEY",
    "AWS_SESSION_TOKEN",
    "KUBECONFIG",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "ACTIONS_RUNTIME_TOKEN",
    "ACTIONS_ID_TOKEN_REQUEST_TOKEN",
)
"""Variables removed from Claude's environment: it reads untrusted logs, so it holds no credential it could leak."""

MAX_SUMMARY_CHARS = 500_000
"""The most of Claude's final answer written to the run's page.

GitHub refuses a step summary over 1 MiB.
"""

MAX_ERROR_CHARS = 500
"""The most of an API error's message printed in the workflow's log."""

PERMISSIONS_FILE = ".github/prompts/pod-log-review.settings.json"
"""Claude Code's permission rules for the review, relative to the repository's root."""

TOOLS = "Read,Grep,Glob,Bash,Skill,TodoWrite"
"""The built-in tools Claude Code may use.

The MCP server's tools come from its configuration.
"""


@dataclass(frozen=True)
class Settings:  # pylint: disable=too-many-instance-attributes
    """
    The review's settings, from the environment that the workflow sets.

    Each field is named after its environment variable. They are read once, by :meth:`from_env`,
    so that the rest of the script never reads the environment itself.
    """

    #: The environment whose pods are reviewed, e.g. ``prod``.
    environment: str
    #: The environment's domain, e.g. ``ubc.smarter.sh``.
    platform_domain: str
    #: The folder of downloaded, redacted logs that ``download-logs.sh`` wrote.
    log_dir: str
    #: How far back each log reaches, e.g. ``25h``, or empty for each container's whole log.
    since: str
    #: The workflow run's url, for the issues' attribution.
    run_url: str
    #: The branch that fix pull requests merge into.
    pr_base: str
    #: The most issues to open.
    max_new_issues: str
    #: The most comments to add to existing issues.
    max_comments: str
    #: The most issues to close.
    max_closed_issues: str
    #: The most fix pull requests to open.
    max_pull_requests: str
    #: The most that one Claude Code run may spend, in US dollars.
    max_budget_usd: str
    #: Whether to write nothing to GitHub, only report.
    dry_run: bool
    #: The Claude model, e.g. ``claude-opus-5-5``.
    claude_model: str
    #: The runner's temporary folder. ``claude/`` in it holds the MCP configuration and the stream.
    runner_temp: str
    #: The file that GitHub shows on the run's page, or ``os.devnull`` outside GitHub Actions.
    github_step_summary: str

    @classmethod
    def from_env(cls) -> "Settings":
        """
        Read the settings from the environment.

        :returns: The settings. A variable that isn't set, or is empty, gets its default: ``alpha``
            for ``PR_BASE``, ``5`` for ``MAX_BUDGET_USD``, the system's temporary folder for
            ``RUNNER_TEMP``, ``os.devnull`` for ``GITHUB_STEP_SUMMARY``, and an empty string for
            the rest.
        """

        def env(name: str, default: str = "") -> str:
            """Return an environment variable, or ``default`` if it isn't set or is empty."""
            return os.environ.get(name, "") or default

        return cls(
            environment=env("ENVIRONMENT"),
            platform_domain=env("PLATFORM_DOMAIN"),
            log_dir=env("LOG_DIR"),
            since=env("SINCE"),
            run_url=env("RUN_URL"),
            pr_base=env("PR_BASE", "alpha"),
            max_new_issues=env("MAX_NEW_ISSUES"),
            max_comments=env("MAX_COMMENTS"),
            max_closed_issues=env("MAX_CLOSED_ISSUES"),
            max_pull_requests=env("MAX_PULL_REQUESTS"),
            max_budget_usd=env("MAX_BUDGET_USD", "5"),
            dry_run=env("DRY_RUN") == "true",
            claude_model=env("CLAUDE_MODEL"),
            runner_temp=env("RUNNER_TEMP", "/tmp"),  # nosec B108: GitHub always sets RUNNER_TEMP
            github_step_summary=env("GITHUB_STEP_SUMMARY", os.devnull),
        )

    @property
    def claude_dir(self) -> str:
        """The folder that holds the MCP configuration, with the GitHub token, and the stream."""
        return os.path.join(self.runner_temp, "claude")

    @property
    def stream_path(self) -> str:
        """Claude Code's stream-json output."""
        return os.path.join(self.claude_dir, "stream.jsonl")


def claude_environment() -> dict[str, str]:
    """
    Return the environment for ``claude``: this one, without credentials, and with one Anthropic credential.

    Prints which credential it chose, never its value.

    :returns: The environment, without :data:`SCRUBBED_ENV`, and with either
        ``CLAUDE_CODE_OAUTH_TOKEN`` (a Claude subscription) or, if that isn't set,
        ``ANTHROPIC_API_KEY`` (API credit), but not both.
    :raises SystemExit: If neither credential is set.
    """
    env = {key: value for key, value in os.environ.items() if key not in SCRUBBED_ENV}
    if env.get("CLAUDE_CODE_OAUTH_TOKEN"):
        print("Claude Code authenticates with CLAUDE_CODE_OAUTH_TOKEN (Claude subscription).")
        env.pop("ANTHROPIC_API_KEY", None)
    elif env.get("ANTHROPIC_API_KEY"):
        print("Claude Code authenticates with ANTHROPIC_API_KEY (API credit).")
        env.pop("CLAUDE_CODE_OAUTH_TOKEN", None)
    else:
        print("::error::Set the CLAUDE_CODE_OAUTH_TOKEN or ANTHROPIC_API_KEY secret.")
        raise SystemExit(1)
    return env


def prompt(settings: Settings) -> str:
    """
    Return the message that starts the review: the run's parameters.

    The instructions themselves are in ``.github/prompts/pod-log-review.md``, which the message
    tells Claude to read first.

    :param settings: The review's settings.
    :returns: The message.
    """
    releases = ", ".join(PodInventory.read(settings.log_dir).releases) or "unknown, see inventory/images.txt"
    if settings.dry_run:
        mode = "DRY RUN: write nothing to GitHub. Report what you would have opened, commented, closed and proposed."
    else:
        mode = "Act: write issues, comments, closings and pull requests within the limits."
    span = f"the last {settings.since}" if settings.since else "the lifetime of the container"
    report = read_report(settings.log_dir)
    if report.get("total"):
        kinds = ", ".join(f"{kind} {count}" for kind, count in report.get("kinds", {}).items())
        redactions = (
            f"{report['total']} ({kinds}) in {len(report.get('files', {}))} file(s), listed in "
            f'{os.path.join(settings.log_dir, REPORT_NAME)}. Each one is a finding: see "Redactions are leaks".'
        )
    else:
        redactions = "none"
    limits = (
        f"{settings.max_new_issues} new issues, {settings.max_comments} comments, "
        f"{settings.max_closed_issues} closed issues, {settings.max_pull_requests} pull requests"
    )
    return "\n".join(
        [
            "Review the pod logs of the Smarter environment below, following "
            ".github/prompts/pod-log-review.md. Read that file first.",
            "",
            f"- Environment: {settings.environment}, https://{settings.platform_domain}",
            f"- Log folder: {settings.log_dir}",
            f"- Each log covers: {span}",
            f"- Deployed release (image tags): {releases}",
            f"- Redactions: {redactions}",
            f"- Date: {datetime.now(timezone.utc):%Y-%m-%d}",
            f"- Workflow run: {settings.run_url}",
            f"- Pull request base branch: {settings.pr_base}",
            f"- Limits for this run: {limits}",
            f"- Mode: {mode}",
            "",
        ]
    )


def claude_command(settings: Settings, message: str) -> list[str]:
    """
    Return the ``claude`` command line for one review.

    The permissions are in :data:`PERMISSIONS_FILE`. Only what depends on this run is here: the
    MCP configuration, the log folder that Claude may read, and the folder that holds the GitHub
    token, which it may not.

    :param settings: The review's settings.
    :param message: The prompt, from :func:`prompt`.
    :returns: The command and its arguments, for :func:`subprocess.run`, without a shell.
    """
    return [
        "claude",
        "-p",
        message,
        "--model",
        settings.claude_model,
        "--settings",
        PERMISSIONS_FILE,
        "--permission-mode",
        "dontAsk",
        "--tools",
        TOOLS,
        "--mcp-config",
        os.path.join(settings.claude_dir, "mcp.json"),
        "--strict-mcp-config",
        "--add-dir",
        settings.log_dir,
        # "//" starts an absolute path in a permission rule: claude_dir is absolute.
        "--disallowedTools",
        f"Read(/{settings.claude_dir}/**)",
        "--max-budget-usd",
        settings.max_budget_usd,
        "--output-format",
        "stream-json",
        "--verbose",
        "--no-session-persistence",
    ]


def review_once(settings: Settings, command: list[str], env: dict[str, str]) -> int:
    """
    Run Claude Code once, replacing the stream with its output.

    :param settings: The review's settings, for the stream's path.
    :param command: The command line, from :func:`claude_command`.
    :param env: The environment, from :func:`claude_environment`.
    :returns: Claude Code's exit status.
    """
    with open(settings.stream_path, "w", encoding="utf-8") as stream:
        return subprocess.run(command, env=env, stdout=stream, check=False).returncode  # nosec B603


def succeeded(status: int, result: ReviewResult | None) -> bool:
    """
    Return whether a review finished without an error.

    :param status: Claude Code's exit status.
    :param result: How the run ended, or None if it never finished.
    """
    return status == 0 and result is not None and not result.is_error


def worth_retrying(result: ReviewResult | None, writes: int) -> bool:
    """
    Return whether a failed review may run again.

    It may if it wrote nothing to GitHub, and it either died before finishing or failed on a
    transient API error. A run that called a write tool is never repeated, because the second run
    would open the same issues again; nor is one that hit its budget or turn limit, which would
    only hit it again.

    :param result: How the run ended, or None if it never finished.
    :param writes: How many times it called a tool that writes to GitHub.
    """
    if writes:
        return False
    return result is None or result.transient_api_error


def run(settings: Settings) -> int:
    """
    Run the review, and run it once more if it failed in a way that is safe to retry.

    Writes the stream to :attr:`Settings.stream_path`, and prints one line per failed attempt,
    with its exit status, how it ended and its number of GitHub writes, but nothing from the
    stream.

    :param settings: The review's settings.
    :returns: The step's exit status: 0 if an attempt succeeded, else 1.
    :raises SystemExit: If no Anthropic credential is set.
    """
    env = claude_environment()
    command = claude_command(settings, prompt(settings))
    for attempt in range(1, ATTEMPTS + 1):
        status = review_once(settings, command, env)
        result = final_result(settings.stream_path)
        if succeeded(status, result):
            return 0
        writes = write_attempts(settings.stream_path)
        ending = result.describe() if result else "did not finish"
        print(f"Attempt {attempt} failed: exit status {status}, {ending}, GitHub writes: {writes}.")
        if attempt == ATTEMPTS or not worth_retrying(result, writes):
            return 1
        print(f"Retrying in {RETRY_DELAY_SECONDS} seconds.")
        time.sleep(RETRY_DELAY_SECONDS)
    return 1


def summarize(settings: Settings) -> int:
    """
    Append Claude's final answer, and the run's turns and cost, to the run's page.

    If the run ended in an error, it also prints why in the workflow's log, with the API error's
    own message when there is one: that text comes from the API, not from the pod logs.

    :param settings: The review's settings.
    :returns: The step's exit status: 1 if the run ended in an error, else 0. A run that never
        finished returns 0, because the step that ran it has already failed.
    """
    result = final_result(settings.stream_path)
    with open(settings.github_step_summary, "a", encoding="utf-8") as summary:
        if result is None:
            summary.write("Claude Code did not finish: see the step above.\n")
            return 0
        answer = (result.answer or "Claude Code returned no summary.")[:MAX_SUMMARY_CHARS]
        summary.write(f"# Pod log review: {settings.environment}\n\n{answer}\n\n---\n{result.describe()}\n")
    if not result.is_error:
        return 0
    print(f"Claude Code failed: {result.describe()}")
    if result.api_error_status and result.answer:
        print(result.answer[:MAX_ERROR_CHARS])
    return 1


def main() -> int:
    """
    Run the command named on the command line, ``run`` or ``summarize``.

    :returns: The command's exit status.
    """
    parser = argparse.ArgumentParser(description=DESCRIPTION)
    parser.add_argument("command", choices=("run", "summarize"), help="run the review, or summarize it")
    args = parser.parse_args()
    settings = Settings.from_env()
    return run(settings) if args.command == "run" else summarize(settings)


if __name__ == "__main__":
    sys.exit(main())
