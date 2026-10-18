"""Helpers of the llmtool signal receivers."""

from smarter.lib import json


def response_characters(response) -> int:
    """Return the length of a tool call's response, as JSON, or of a string response."""
    if response is None:
        return 0
    if isinstance(response, str):
        return len(response)
    return len(json.dumps(response))
