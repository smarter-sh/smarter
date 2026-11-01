"""Read what an unattended Claude Code pod log review produced, and the logs it reviewed.

The daily pod log review (``.github/workflows/podLogReview.yml``) runs ``claude -p
--output-format stream-json --verbose``, which writes one JSON event per line: the system's
initialization, each assistant turn and its tool calls, each tool result, and finally one
``result`` event with Claude's final answer and whether the run ended in an error. This module
reads that stream, and the log folder that ``download-logs.sh`` wrote, for the workflow's two
scripts:

- ``pod_log_review.py`` decides from :func:`final_result` and :func:`write_attempts` whether a failed
  run may be retried, and writes the final answer to the run's page;
- ``pod_log_review_slack.py`` lists the GitHub writes that succeeded, or, on a clean run, posts the facts of
  :class:`PodInventory`.

Every reader tolerates a damaged stream: a line that isn't a JSON object, such as the last line of
a process that was killed mid-write, is skipped rather than raised. The stream holds the pod logs,
which anyone can write into, so nothing here prints any of it.

Like every script in ``scripts/``, it uses only the standard library, because the runner has no
virtual environment. The workflow runs the scripts with ``python3 -E -s``, which ignores
``PYTHONPATH`` and the user's site-packages but, unlike ``-I``, keeps the script's own folder on
``sys.path``, so that they import this module by name.

It uses only Python's standard library, which comes with every Python install:

- ``json`` decodes each line of the stream into Python dicts and lists.
- ``os`` lists folders (``os.listdir``) and joins paths (``os.path.join``).
- ``re`` is regular expressions: :data:`IMAGE_TAG` says what a safe image tag looks like.
- ``dataclasses.dataclass`` writes a class's ``__init__`` from its annotated fields, as in
  :class:`ReviewResult` and :class:`PodInventory`; ``field(default_factory=dict)`` gives each
  instance its own empty dict, rather than one shared by all of them.
- ``collections.abc.Iterator`` and ``typing.TypeVar`` are only for type annotations, which tools
  such as Pylance check and Python itself ignores: :func:`events` returns an ``Iterator``, values
  produced one at a time, and the ``TypeVar`` ``T`` says that :func:`typed` returns the type it was
  asked for, e.g. ``typed(value, str)`` returns a ``str`` or None.
"""

import json
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from typing import TypeVar

T = TypeVar("T")

JsonObject = dict[str, object]
"""One decoded JSON object of the stream, whose values are checked with :func:`typed` before use."""

WRITE_TOOLS = ("create_issue", "comment_on_issue", "close_issue", "create_pull_request")
"""The Smarter Project MCP server's tools that write to GitHub, without their ``mcp__<server>__`` prefix."""

HEALTHY_VERDICT = "verdict: healthy"
"""The last line of the final answer of a run that found nothing to fix, as ``.github/prompts/pod-log-review.md`` asks for it."""

IMAGE_TAG = re.compile(r"^[\w.+-]{1,64}$")
"""An image tag that is safe to show in a message: no spaces, markup or other punctuation."""


def typed(value: object, kind: type[T] | tuple[type[T], ...]) -> T | None:
    """
    Return a JSON value if it is of the expected type, or None.

    ``True`` and ``False`` are not numbers here, although Python's ``bool`` is a subclass of ``int``.

    :param value: A value from a decoded event.
    :param kind: The expected type, e.g. ``str``, or types, e.g. ``(int, float)`` for any number.
    :returns: The value, or None if it is missing or of another type.
    """
    if not isinstance(value, kind):
        return None
    if isinstance(value, bool) and kind is not bool:
        return None
    return value


@dataclass(frozen=True)
class ReviewResult:
    """
    The final ``result`` event of a Claude Code run: how it ended, and Claude's final answer.

    Claude Code writes it once, as the stream's last event, whether the run succeeded or not. A run
    that was killed has none: see :func:`final_result`.
    """

    #: Whether the run ended in an error: an API error, the budget or the turn limit.
    is_error: bool
    #: Claude's final answer, in Markdown, or the error's message. None if the event had no text.
    answer: str | None = None
    #: The HTTP status of the Anthropic API error that ended the run, e.g. ``529``, or None.
    api_error_status: int | None = None
    #: How the run ended, e.g. ``success`` or ``error_max_budget_usd``, or None.
    subtype: str | None = None
    #: Why Claude Code stopped, when it says, or None.
    terminal_reason: str | None = None
    #: The number of turns the run took, or None.
    num_turns: int | None = None
    #: What the run cost, in US dollars, or None.
    total_cost_usd: float | None = None

    @classmethod
    def from_event(cls, event: JsonObject) -> "ReviewResult":
        """
        Build a result from a ``result`` event, keeping only fields of the expected type.

        :param event: A decoded event whose ``type`` is ``result``.
        :returns: The result. A field that is missing, or of an unexpected type, is None.
        """
        return cls(
            is_error=event.get("is_error") is True,
            answer=typed(event.get("result"), str),
            api_error_status=typed(event.get("api_error_status"), int),
            subtype=typed(event.get("subtype"), str),
            terminal_reason=typed(event.get("terminal_reason"), str),
            num_turns=typed(event.get("num_turns"), int),
            # JSON writes a whole number of dollars, e.g. 0, as an int.
            total_cost_usd=typed(event.get("total_cost_usd"), (int, float)),
        )

    @property
    def transient_api_error(self) -> bool:
        """Whether the run ended on an API error that a later attempt may not get: 429 rate limited, or a 5xx such as 529 overloaded."""
        status = self.api_error_status
        return status is not None and (status == 429 or 500 <= status <= 599)

    def describe(self) -> str:
        """
        Return the run's turns and cost, and why it failed, for the workflow's log and the run's page.

        :returns: E.g. ``turns: 9, cost: $1.20``, or for a failed run ``turns: ?, cost: $?, failed:
            subtype error_max_budget_usd, terminal_reason ?, api_error_status none``.
        """
        turns = "?" if self.num_turns is None else self.num_turns
        cost = "?" if self.total_cost_usd is None else f"{self.total_cost_usd:.2f}"
        text = f"turns: {turns}, cost: ${cost}"
        if self.is_error:
            text += (
                f", failed: subtype {self.subtype or '?'}, terminal_reason {self.terminal_reason or '?'}, "
                f"api_error_status {self.api_error_status or 'none'}"
            )
        return text

    @property
    def healthy(self) -> bool:
        """
        Whether the run succeeded, and Claude's final answer ends with the healthy verdict.

        The last non-empty line must be exactly ``Verdict: healthy``, ignoring case and Markdown
        emphasis (``*``, ``_``, backticks). Any other ending, such as ``Verdict: healthy, but ...``,
        is not healthy, so that only the verdict, never free text, decides it.
        """
        if self.is_error or not self.answer:
            return False
        lines = [line.strip() for line in self.answer.splitlines() if line.strip()]
        return bool(lines) and lines[-1].strip("*_` ").lower() == HEALTHY_VERDICT


@dataclass
class PodInventory:
    """
    Facts about the reviewed pods, read from the log folder that ``download-logs.sh`` wrote.

    They come from kubectl (``inventory/pods.txt`` and ``inventory/images.txt``) and from the
    names of the downloaded logs, not from the logs' contents, so they are safe to show in a
    message. A fact that can't be read is left empty rather than raised: the inventory only
    decorates a message.
    """

    #: The number of reviewed pods of each deployment, e.g. ``{"smarter": 2, "smarter-beat": 1}``.
    pods: dict[str, int] = field(default_factory=dict)
    #: The reviewed pods' restarts in total, or None if ``inventory/pods.txt`` couldn't be read.
    restarts: int | None = None
    #: The image tags of the ReplicaSets that have replicas, i.e. the deployed release, in order.
    releases: list[str] = field(default_factory=list)

    @classmethod
    def read(cls, log_dir: str) -> "PodInventory":
        """
        Read the inventory of a log folder.

        :param log_dir: The folder that ``download-logs.sh`` wrote: one folder per deployment, with
            one ``<pod>.log`` per pod, and ``inventory/``. An empty string, or a folder that doesn't
            exist, gives an empty inventory.
        :returns: The inventory.
        """
        if not log_dir or not os.path.isdir(log_dir):
            return cls()
        pods = pods_by_deployment(log_dir)
        names = {pod for deployment_pods in pods.values() for pod in deployment_pods}
        return cls(
            pods={deployment: len(deployment_pods) for deployment, deployment_pods in pods.items()},
            restarts=total_restarts(os.path.join(log_dir, "inventory", "pods.txt"), names),
            releases=running_releases(os.path.join(log_dir, "inventory", "images.txt")),
        )


def read_rows(path: str) -> list[list[str]] | None:
    """
    Return a kubectl listing as rows of whitespace-separated columns.

    :param path: A file of ``inventory/``.
    :returns: Its rows, or None if it can't be read.
    """
    try:
        with open(path, encoding="utf-8") as listing:
            return [row.split() for row in listing]
    except OSError:
        return None


def pods_by_deployment(log_dir: str) -> dict[str, list[str]]:
    """
    Return the reviewed pods of each deployment, from the names of their logs.

    A ``<pod>.previous.log``, the log from before a restart, is not another pod.

    :param log_dir: The log folder.
    :returns: Each deployment that has pods, and its pods' names.
    """
    pods: dict[str, list[str]] = {}
    for deployment in sorted(os.listdir(log_dir)):
        folder = os.path.join(log_dir, deployment)
        if deployment == "inventory" or not os.path.isdir(folder):
            continue
        logs = [name for name in os.listdir(folder) if name.endswith(".log") and not name.endswith(".previous.log")]
        if logs:
            pods[deployment] = [name.removesuffix(".log") for name in logs]
    return pods


def total_restarts(path: str, pod_names: set[str]) -> int | None:
    """
    Return the reviewed pods' restarts in total, from ``kubectl get pods -o wide``.

    Its columns are ``NAME READY STATUS RESTARTS ...``, where ``RESTARTS`` may be followed by
    ``(3h ago)``. Pods that weren't reviewed, such as a finished init job, are not counted.

    :param path: ``inventory/pods.txt``.
    :param pod_names: The names of the reviewed pods.
    :returns: The total, or None if the file can't be read.
    """
    rows = read_rows(path)
    if rows is None:
        return None
    return sum(int(row[3]) for row in rows if len(row) > 3 and row[0] in pod_names and row[3].isdigit())


def running_releases(path: str) -> list[str]:
    """
    Return the image tags of the ReplicaSets that have replicas, i.e. the deployed release.

    Each deployment's section starts with ``== <deployment>``, followed by one line per
    ReplicaSet: ``<created> <replicas> <image>``. Old ReplicaSets have 0 replicas.

    :param path: ``inventory/images.txt``.
    :returns: The tags, each once, in order, or an empty list if the file can't be read.
    """
    tags: list[str] = []
    for row in read_rows(path) or []:
        if len(row) != 3 or not row[1].isdigit() or int(row[1]) == 0 or ":" not in row[2]:
            continue
        tag = row[2].rpartition(":")[2]
        if IMAGE_TAG.match(tag) and tag not in tags:
            tags.append(tag)
    return tags


def tool_name(name: str) -> str:
    """
    Return a tool's name without its MCP prefix.

    :param name: The name in a ``tool_use`` block, e.g. ``mcp__smarter-project__create_issue``.
    :returns: The tool's own name, e.g. ``create_issue``. A name without a prefix is returned as is.
    """
    return name.rsplit("__", 1)[-1]


def events(path: str) -> Iterator[JsonObject]:
    """
    Yield each event of a stream, in order, skipping lines that aren't a JSON object.

    :param path: The stream-json output of the run.
    :returns: An iterator of the decoded events. A file that doesn't exist yields nothing.
    """
    if not os.path.isfile(path):
        return
    with open(path, encoding="utf-8", errors="replace") as stream:
        for raw in stream:
            try:
                event = json.loads(raw)
            except ValueError:
                continue
            if isinstance(event, dict):
                yield event


def content_blocks(event: JsonObject) -> list[JsonObject]:
    """
    Return the content blocks of an assistant or user event: text, ``tool_use`` or ``tool_result``.

    :param event: A decoded event.
    :returns: Its ``message.content`` blocks that are objects, or an empty list for an event
        without them, such as ``system`` or ``result``.
    """
    message = event.get("message")
    content = message.get("content") if isinstance(message, dict) else None
    if not isinstance(content, list):
        return []
    return [block for block in content if isinstance(block, dict)]


def final_result(path: str) -> ReviewResult | None:
    """
    Return how the run ended, from its last ``result`` event.

    :param path: The stream-json output of the run.
    :returns: The result, or None if the run never finished, e.g. because it was killed, or the
        stream doesn't exist.
    """
    last: JsonObject | None = None
    for event in events(path):
        if event.get("type") == "result":
            last = event
    return ReviewResult.from_event(last) if last is not None else None


def write_attempts(path: str) -> int:
    """
    Return how many times the run called a tool that writes to GitHub, whether or not it succeeded.

    Used to decide whether a failed run may be repeated: a call that the stream shows may have
    reached GitHub even if its result never came back, so every call counts.

    :param path: The stream-json output of the run.
    :returns: The number of calls of :data:`WRITE_TOOLS`.
    """
    return sum(
        1
        for event in events(path)
        for block in content_blocks(event)
        if block.get("type") == "tool_use" and tool_name(str(block.get("name", ""))) in WRITE_TOOLS
    )
