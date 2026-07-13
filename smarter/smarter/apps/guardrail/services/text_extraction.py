"""Extract and rewrite scannable text segments within guardrail payloads.

Flattens a pre/post payload into a list of ``(path, text)`` segments for
guardrails to scan, and writes redacted/transformed text back into a
payload copy at the same path.

Isolating this in one place means every strategy scans the same surface
consistently, and :class:`~smarter.apps.guardrail.models.GuardrailAction`
``REDACT``/``TRANSFORM`` actions can round-trip through the same path
syntax used for extraction.
"""

import copy
from typing import Any

from smarter.apps.guardrail.services.contracts import GuardrailStage, TextSegment


def extract_segments(payload: dict[str, Any], stage: GuardrailStage) -> list[TextSegment]:
    """Return the scannable text segments for a given payload and stage.

    :param payload: The pre-completion request body or post-completion
        response body to scan, as a plain ``dict`` (already validated
        against :class:`~smarter.apps.guardrail.services.contracts.PreCompletionPayload`
        or :class:`~smarter.apps.guardrail.services.contracts.PostCompletionPayload`
        upstream).
    :type payload: dict[str, typing.Any]
    :param stage: Which side of the model call ``payload`` represents.
        Determines whether the request-shaped or response-shaped
        extraction rules are applied.
    :type stage: ~smarter.apps.guardrail.services.contracts.GuardrailStage
    :returns: One :class:`~smarter.apps.guardrail.services.contracts.TextSegment`
        per scannable string found in ``payload``, in document order.
        Empty, missing, or non-string fields are omitted.
    :rtype: list[~smarter.apps.guardrail.services.contracts.TextSegment]
    """
    if stage == GuardrailStage.PRE:
        return _extract_pre_segments(payload)
    return _extract_post_segments(payload)


def _extract_pre_segments(payload: dict[str, Any]) -> list[TextSegment]:
    """Extract text segments from a pre-completion request payload.

    :param payload: A pre-completion request body, e.g. the
        ``messages``/``functions`` shape sent to the LLM provider.
    :type payload: dict[str, typing.Any]
    :returns: A segment for each non-empty ``messages[i].content`` and
        ``functions[i].description`` string in ``payload``.
    :rtype: list[~smarter.apps.guardrail.services.contracts.TextSegment]
    """
    segments: list[TextSegment] = []

    for i, message in enumerate(payload.get("messages") or []):
        content = message.get("content")
        if isinstance(content, str) and content:
            segments.append(TextSegment(path=f"messages[{i}].content", text=content))

    for i, function in enumerate(payload.get("functions") or []):
        description = function.get("description")
        if isinstance(description, str) and description:
            segments.append(TextSegment(path=f"functions[{i}].description", text=description))

    return segments


def _extract_post_segments(payload: dict[str, Any]) -> list[TextSegment]:
    """Extract text segments from a post-completion response payload.

    :param payload: A post-completion response body, e.g. the
        ``choices`` shape returned by the LLM provider.
    :type payload: dict[str, typing.Any]
    :returns: A segment for each non-empty ``choices[i].message.content``
        and ``choices[i].message.refusal`` string in ``payload``.
    :rtype: list[~smarter.apps.guardrail.services.contracts.TextSegment]
    """
    segments: list[TextSegment] = []

    for i, choice in enumerate(payload.get("choices") or []):
        message = choice.get("message") or {}
        content = message.get("content")
        if isinstance(content, str) and content:
            segments.append(TextSegment(path=f"choices[{i}].message.content", text=content))

        refusal = message.get("refusal")
        if isinstance(refusal, str) and refusal:
            segments.append(TextSegment(path=f"choices[{i}].message.refusal", text=refusal))

    return segments


def write_segment(payload: dict[str, Any], path: str, new_text: str) -> dict[str, Any]:
    """Return a deep-copied payload with the text at ``path`` replaced.

    :param payload: The payload to modify. Never mutated in place — the
        caller's original ``payload`` is left untouched.
    :type payload: dict[str, typing.Any]
    :param path: A path in the ``"messages[0].content"`` /
        ``"choices[0].message.content"`` grammar produced by
        :func:`extract_segments`.
    :type path: str
    :param new_text: The replacement text to write at ``path``.
    :type new_text: str
    :returns: A deep copy of ``payload`` with the text at ``path``
        replaced by ``new_text``. If ``path`` does not resolve to an
        existing field, the copy is returned unchanged — this function
        fails open on the write side, since the triggering finding has
        already been recorded by the caller regardless of whether the
        write succeeds.
    :rtype: dict[str, typing.Any]
    """
    updated = copy.deepcopy(payload)
    node, key = resolve_path(updated, path)
    if node is not None and key is not None:
        node[key] = new_text
    return updated


def resolve_path(payload: dict[str, Any], path: str) -> tuple[Any, Any]:
    """Walk a ``"messages[0].content"``-style path to its final container.

    :param payload: The payload to walk.
    :type payload: dict[str, typing.Any]
    :param path: A path in the ``"messages[0].content"`` /
        ``"choices[0].message.content"`` grammar produced by
        :func:`extract_segments`.
    :type path: str
    :returns: A ``(container, key)`` pair such that
        ``container[key]`` addresses the field named by ``path``,
        letting the caller assign ``container[key] = value`` directly.
        Returns ``(None, None)`` if ``path`` is empty or does not
        resolve against ``payload`` (e.g. an out-of-range index or a
        missing field).
    :rtype: tuple[typing.Any, typing.Any]
    """
    tokens = _tokenize(path)
    node: Any = payload
    for token in tokens[:-1]:
        try:
            node = node[token]
        except (KeyError, IndexError, TypeError):
            return None, None
    if not tokens:
        return None, None
    return node, tokens[-1]


def _tokenize(path: str) -> list[Any]:
    """Split a dotted/bracketed path string into its component tokens.

    :param path: A path such as ``"messages[0].content"``.
    :type path: str
    :returns: The path broken into alternating field names (``str``)
        and list indices (``int``), e.g. ``["messages", 0, "content"]``
        for the example above.
    :rtype: list[typing.Any]
    """
    tokens: list[Any] = []
    for part in path.replace("]", "").split("."):
        if "[" in part:
            name, idx = part.split("[")
            tokens.append(name)
            tokens.append(int(idx))
        else:
            tokens.append(part)
    return tokens


__all__ = ["extract_segments", "write_segment", "resolve_path"]
