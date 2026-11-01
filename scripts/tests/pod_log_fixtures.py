"""Fake Claude Code streams and log folders, for the tests of the pod log review's scripts."""

import json
from collections.abc import Sequence
from pathlib import Path

from pod_log_review_stream import JsonObject

HEALTHY_ANSWER = "## Health\n\nAll good.\n\n**Verdict: healthy**\n"
"""A final answer that ends with the healthy verdict, in bold, as Claude may write it."""


def result_event(answer: str = HEALTHY_ANSWER, is_error: bool = False, **fields: object) -> JsonObject:
    """
    Return a ``result`` event, as Claude Code writes it last.

    :param answer: Claude's final answer, or the error's message.
    :param is_error: Whether the run ended in an error.
    :param fields: Other fields, e.g. ``api_error_status=529``.
    """
    return {"type": "result", "is_error": is_error, "result": answer, **fields}


def write_call(tool: str = "create_issue", call_id: str = "t1") -> JsonObject:
    """
    Return an assistant event that calls one of the MCP server's tools.

    :param tool: The tool's name, without its ``mcp__smarter-project__`` prefix.
    :param call_id: The call's id, which its result names.
    """
    block = {"type": "tool_use", "id": call_id, "name": f"mcp__smarter-project__{tool}"}
    return {"type": "assistant", "message": {"content": [block]}}


def write_result(text: str, call_id: str = "t1", is_error: bool = False) -> JsonObject:
    """
    Return a user event that holds a tool's result.

    :param text: The result's text, e.g. ``Opened issue #42 ...`` and its link.
    :param call_id: The id of the call it answers.
    :param is_error: Whether the tool failed.
    """
    block = {"type": "tool_result", "tool_use_id": call_id, "content": text, "is_error": is_error}
    return {"type": "user", "message": {"content": [block]}}


def write_stream(path: Path, events: Sequence[JsonObject | str]) -> str:
    """
    Write a stream-json file, one event per line.

    :param path: Where to write it.
    :param events: The events. A string is written as is, e.g. a line cut off mid-write.
    :returns: The path, as a string.
    """
    lines = [event if isinstance(event, str) else json.dumps(event) for event in events]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return str(path)


def write_log_dir(root: Path, worker_restarts: int = 0) -> str:
    """
    Write a log folder as ``download-logs.sh`` does: 4 pods of 3 deployments, and their inventory.

    The worker has a ``.previous.log``, which is not another pod; ``pods.txt`` also lists a finished
    init job, which wasn't reviewed; ``images.txt`` has an old ReplicaSet with 0 replicas.

    :param root: The folder to write into.
    :param worker_restarts: The worker pod's restarts.
    :returns: The log folder, as a string.
    """
    logs = root / "logs"
    for name in (
        "smarter/smarter-abc-1.log",
        "smarter/smarter-abc-2.log",
        "smarter-worker/smarter-worker-x-1.log",
        "smarter-worker/smarter-worker-x-1.previous.log",
        "smarter-beat/smarter-beat-z-1.log",
    ):
        (logs / name).parent.mkdir(parents=True, exist_ok=True)
        (logs / name).write_text("", encoding="utf-8")
    (logs / "inventory").mkdir()
    (logs / "inventory" / "pods.txt").write_text(
        "NAME                 READY   STATUS      RESTARTS      AGE\n"
        "smarter-abc-1        1/1     Running     0             2d\n"
        "smarter-abc-2        1/1     Running     0             2d\n"
        f"smarter-worker-x-1   1/1     Running     {worker_restarts} (5h ago)    2d\n"
        "smarter-beat-z-1     1/1     Running     0             2d\n"
        "smarter-job-init-q   0/1     Completed   3             2d\n",
        encoding="utf-8",
    )
    (logs / "inventory" / "images.txt").write_text(
        "== smarter\n"
        "2026-10-01T00:00:00Z 0 registry.example/smarter:v0.40.3\n"
        "2026-10-30T00:00:00Z 2 registry.example/smarter:v0.40.4\n"
        "== smarter-worker\n"
        "2026-10-30T00:00:00Z 1 registry.example/smarter:v0.40.4\n",
        encoding="utf-8",
    )
    return str(logs)
