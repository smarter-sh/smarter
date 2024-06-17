"""Docs utils."""


def manifest_path(kind: str) -> str:
    return f"manifest/{kind}/".lower()


def manifest_name(kind: str) -> str:
    return f"api_docs_manifest_{kind}".lower()


def json_schema_path(kind: str) -> str:
    return f"json-schema/{kind}/".lower()


def json_schema_name(kind: str) -> str:
    return f"api_docs_json_schema_{kind}".lower()
