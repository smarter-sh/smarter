"""
Extract the text that guardrails scan from a chat completion request or response, and write guardrails' changes back.

- Input guardrails scan the **latest user message**: what the user just said. They do not
  scan the LLMClient's own system prompt, which would make e.g. a prompt injection guardrail
  trigger on the operator's instructions, nor the earlier turns of the conversation, which
  were scanned when they were new.
- Output guardrails scan the reply's message content, and refusal.

A message's content may be a string, or a list of parts, of which the ``text`` parts are
scanned. Each segment has a path, e.g. ``messages[3].content`` or
``messages[3].content[0].text``, so that redactions can be written back to the right place.
"""

import copy
import re
from typing import Any

from smarter.apps.provider.services.text_completion.contracts import (
    GuardrailStage,
    TextSegment,
)

USER_ROLE = "user"


def extract_segments(payload: dict[str, Any], stage: GuardrailStage) -> list[TextSegment]:
    """
    Return the text segments that guardrails scan, for a payload and stage.

    :param payload: A chat completion request (``messages``) for the pre stage, or response
        (``choices``) for the post stage.
    :param stage: Which side of the model call the payload is.
    :returns: The segments, in document order. Empty or non-text fields are omitted.
    """
    if stage == GuardrailStage.PRE:
        return extract_pre_segments(payload)
    return extract_post_segments(payload)


def content_segments(content: Any, path: str) -> list[TextSegment]:
    """Return the segments of a message's content: a string, or a list of parts."""
    if isinstance(content, str):
        return [TextSegment(path=path, text=content)] if content else []
    segments = []
    if isinstance(content, list):
        for i, part in enumerate(content):
            if isinstance(part, dict) and part.get("type") == "text" and isinstance(part.get("text"), str):
                if part["text"]:
                    segments.append(TextSegment(path=f"{path}[{i}].text", text=part["text"]))
    return segments


def latest_user_message_index(messages: list[Any]) -> int | None:
    """Return the index of the latest message whose role is user, or ``None``."""
    for i in range(len(messages) - 1, -1, -1):
        message = messages[i]
        if isinstance(message, dict) and message.get("role") == USER_ROLE:
            return i
    return None


def extract_pre_segments(payload: dict[str, Any]) -> list[TextSegment]:
    """Return the segments of the latest user message of a chat completion request."""
    messages = payload.get("messages") or []
    index = latest_user_message_index(messages)
    if index is None:
        return []
    return content_segments(messages[index].get("content"), f"messages[{index}].content")


def extract_post_segments(payload: dict[str, Any]) -> list[TextSegment]:
    """Return the segments of each choice's message content, and refusal, of a chat completion response."""
    segments: list[TextSegment] = []
    for i, choice in enumerate(payload.get("choices") or []):
        message = (choice or {}).get("message") or {}
        segments.extend(content_segments(message.get("content"), f"choices[{i}].message.content"))
        refusal = message.get("refusal")
        if isinstance(refusal, str) and refusal:
            segments.append(TextSegment(path=f"choices[{i}].message.refusal", text=refusal))
    return segments


def write_segment(payload: dict[str, Any], path: str, new_text: str) -> dict[str, Any]:
    """
    Return a deep copy of the payload, with the text at ``path`` replaced.

    If ``path`` does not resolve, the copy is returned unchanged.
    """
    updated = copy.deepcopy(payload)
    node, key = resolve_path(updated, path)
    if node is not None and key is not None:
        node[key] = new_text
    return updated


def read_segment(payload: dict[str, Any], path: str) -> str | None:
    """Return the text at ``path``, or ``None`` if it does not resolve to a string."""
    node, key = resolve_path(payload, path)
    if node is None:
        return None
    try:
        value = node[key]
    except (KeyError, IndexError, TypeError):
        return None
    return value if isinstance(value, str) else None


def resolve_path(payload: Any, path: str) -> tuple[Any, Any]:
    """
    Walk a ``messages[0].content``-style path to its final container.

    :returns: ``(container, key)``, such that ``container[key]`` is the field that ``path``
        names, or ``(None, None)`` if the path does not resolve.
    """
    tokens = tokenize(path)
    if not tokens:
        return None, None
    node: Any = payload
    for token in tokens[:-1]:
        try:
            node = node[token]
        except (KeyError, IndexError, TypeError):
            return None, None
    return node, tokens[-1]


def tokenize(path: str) -> list[Any]:
    """Split a dotted, bracketed path into its keys and indices, e.g. ``a[0].b`` into ``["a", 0, "b"]``."""
    tokens: list[Any] = []
    for part in path.split("."):
        name, _, rest = part.partition("[")
        if name:
            tokens.append(name)
        for index in re.findall(r"(\d+)\]", "[" + rest if rest else ""):
            tokens.append(int(index))
    return tokens


__all__ = ["extract_segments", "read_segment", "resolve_path", "write_segment", "latest_user_message_index"]
