"""Docs utils."""


def manifest_path(kind: str) -> str:
    return f"manifest/{kind}/".lower()


def manifest_name(kind: str) -> str:
    return f"manifest_{kind}".lower()


def json_schema_path(kind: str) -> str:
    return f"json-schema/{kind}/".lower()


def json_schema_name(kind: str) -> str:
    return f"json_schema_{kind}".lower()
