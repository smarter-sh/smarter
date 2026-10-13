"""
The JSON Schemas of the SAM manifests, one per kind, generated from their Pydantic models, and an example manifest of each kind.

``manage.py export_api_contract`` writes them to ``sam/<Kind>.schema.json`` and
``sam/<Kind>.example.json``, beside this module, and a test fails if a committed file is out of
date.

- A schema is exactly the ``data`` of the cli's ``json-schema/<Kind>/`` response, so a client may
  read either. The SDKs generate their manifest models from them, and
  :mod:`smarter.apps.api.v1.contract.openapi` includes them in the OpenAPI document.
- An example is the ``data`` of the cli's ``example-manifest/<Kind>/`` response, without its
  read-only ``status``, whose timestamps change on every request. The SDKs test their generated
  models against them, and a test checks that each example is valid under its kind's schema.
"""

import glob
import json
import os

from django.test import RequestFactory
from pydantic import BaseModel

from smarter.lib.typing import SmarterDictType

from .const import (
    SAM_EXAMPLE_HOST,
    SAM_EXAMPLE_SUFFIX,
    SAM_SCHEMA_DIR,
    SAM_SCHEMA_SUFFIX,
)


def sam_models() -> dict[str, type[BaseModel]]:
    """
    The Pydantic model of each SAM kind: the model that its broker validates manifests with.

    The brokers are imported here, rather than at the module's top, because they import most of
    the platform's apps.

    :returns: The models, by kind, e.g. ``{"Guardrail": SAMGuardrail, ...}``, sorted by kind.
    :rtype: dict[str, type[BaseModel]]
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.brokers import Brokers

    return {kind: Brokers.get_broker(kind)._pydantic_model for kind in sorted(Brokers.all_brokers())}  # type: ignore[union-attr]


def sam_schema(kind: str) -> SmarterDictType:
    """
    A SAM kind's JSON Schema (draft 2020-12): the schema that the cli's ``json-schema`` command returns.

    :param kind: The kind, e.g. Guardrail.
    :type kind: str
    :returns: The schema.
    :rtype: SmarterDictType
    :raises KeyError: If ``kind`` is not a SAM kind.
    """
    return sam_models()[kind].model_json_schema()


def sam_schema_json(kind: str) -> str:
    """
    A SAM kind's JSON Schema, as the text of ``sam/<Kind>.schema.json``.

    :param kind: The kind, e.g. Guardrail.
    :type kind: str
    :returns: The schema, as indented JSON, with a final newline.
    :rtype: str
    """
    return json.dumps(sam_schema(kind), indent=2, sort_keys=True) + "\n"


def sam_example(kind: str) -> SmarterDictType:
    """
    A SAM kind's example manifest, without its read-only ``status``.

    It is rendered in-process by the cli's public ``example-manifest`` view, so that it is exactly
    what the api returns, because the brokers build their examples for a request.

    :param kind: The kind, e.g. Guardrail.
    :type kind: str
    :returns: The manifest.
    :rtype: SmarterDictType
    :raises KeyError: If ``kind`` is not a SAM kind.
    :raises ValueError: If the view does not return an example.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.api.v1.cli.views.manifest import ApiV1CliManifestApiView

    sam_models()[kind]  # pylint: disable=expression-not-assigned
    request = RequestFactory().post(f"/api/v1/cli/example-manifest/{kind}/", HTTP_HOST=SAM_EXAMPLE_HOST)
    response = ApiV1CliManifestApiView.as_view()(request, kind=kind)
    body = json.loads(response.content)
    manifest = body.get("data") if isinstance(body, dict) else None
    if response.status_code != 200 or not isinstance(manifest, dict):
        raise ValueError(f"No example manifest of {kind}: {response.status_code} {body}")
    manifest.pop("status", None)
    return manifest


def sam_example_json(kind: str) -> str:
    """
    A SAM kind's example manifest, as the text of ``sam/<Kind>.example.json``.

    :param kind: The kind, e.g. Guardrail.
    :type kind: str
    :returns: The manifest, as indented JSON, with a final newline.
    :rtype: str
    """
    return json.dumps(sam_example(kind), indent=2, sort_keys=True) + "\n"


def sam_example_path(kind: str, directory: str = SAM_SCHEMA_DIR) -> str:
    """
    The file of a SAM kind's example manifest.

    :param kind: The kind, e.g. Guardrail.
    :type kind: str
    :param directory: The folder of the examples.
    :type directory: str
    :returns: e.g. ``.../sam/Guardrail.example.json``.
    :rtype: str
    """
    return os.path.join(directory, f"{kind}{SAM_EXAMPLE_SUFFIX}")


def sam_schema_path(kind: str, directory: str = SAM_SCHEMA_DIR) -> str:
    """
    The file of a SAM kind's JSON Schema.

    :param kind: The kind, e.g. Guardrail.
    :type kind: str
    :param directory: The folder of the schemas.
    :type directory: str
    :returns: e.g. ``.../sam/Guardrail.schema.json``.
    :rtype: str
    """
    return os.path.join(directory, f"{kind}{SAM_SCHEMA_SUFFIX}")


def write_sam_schemas(directory: str = SAM_SCHEMA_DIR) -> list[str]:
    """
    Write every SAM kind's JSON Schema and example manifest, and remove the files of kinds that no longer exist.

    :param directory: The folder to write. Defaults to ``sam/``, beside this module.
    :type directory: str
    :returns: The paths that were written, sorted by kind, each kind's schema before its example.
    :rtype: list[str]
    """
    os.makedirs(directory, exist_ok=True)
    paths = []
    for kind in sam_models():
        for path, text in (
            (sam_schema_path(kind, directory), sam_schema_json(kind)),
            (sam_example_path(kind, directory), sam_example_json(kind)),
        ):
            with open(path, "w", encoding="utf-8") as file:
                file.write(text)
            paths.append(path)
    existing = glob.glob(os.path.join(directory, f"*{SAM_SCHEMA_SUFFIX}")) + glob.glob(
        os.path.join(directory, f"*{SAM_EXAMPLE_SUFFIX}")
    )
    for stale in set(existing) - set(paths):
        os.remove(stale)
    return paths


__all__ = [
    "sam_example",
    "sam_example_json",
    "sam_example_path",
    "sam_models",
    "sam_schema",
    "sam_schema_json",
    "sam_schema_path",
    "write_sam_schemas",
]
