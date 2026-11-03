"""Docs utils."""


def manifest_path(kind: str) -> str:
    """
    The url path of a kind's example manifest page.

    :param kind: The SAM kind, e.g. ``LLMClient``.
    :returns: The lower-cased path, e.g. ``manifest/llmclient/``.
    """
    return f"manifest/{kind}/".lower()


def manifest_name(kind: str) -> str:
    """
    The url name of a kind's example manifest page.

    :param kind: The SAM kind, e.g. ``LLMClient``.
    :returns: The lower-cased name, e.g. ``manifest_llmclient``.
    """
    return f"manifest_{kind}".lower()


def json_schema_path(kind: str) -> str:
    """
    The url path of a kind's JSON Schema page.

    :param kind: The SAM kind, e.g. ``LLMClient``.
    :returns: The lower-cased path, e.g. ``json-schema/llmclient/``.
    """
    return f"json-schema/{kind}/".lower()


def json_schema_name(kind: str) -> str:
    """
    The url name of a kind's JSON Schema page.

    :param kind: The SAM kind, e.g. ``LLMClient``.
    :returns: The lower-cased name, e.g. ``json_schema_llmclient``.
    """
    return f"json_schema_{kind}".lower()
