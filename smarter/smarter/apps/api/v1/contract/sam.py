"""
The JSON Schemas of the SAM manifests, one per kind, generated from their Pydantic models.

``manage.py export_api_contract`` writes them to ``sam/<Kind>.schema.json``, beside this module,
and a test fails if a committed file is out of date. Each file is exactly the ``data`` of the cli's
``json-schema/<Kind>/`` response, so a client may read either. The SDKs generate their manifest
models from them, and :mod:`smarter.apps.api.v1.contract.openapi` includes them in the OpenAPI
document.
"""

import glob
import json
import os

from pydantic import BaseModel

from smarter.lib.typing import SmarterDictType

from .const import SAM_SCHEMA_DIR, SAM_SCHEMA_SUFFIX


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
    Write every SAM kind's JSON Schema, and remove the schemas of kinds that no longer exist.

    :param directory: The folder to write. Defaults to ``sam/``, beside this module.
    :type directory: str
    :returns: The paths that were written, sorted by kind.
    :rtype: list[str]
    """
    os.makedirs(directory, exist_ok=True)
    paths = []
    for kind in sam_models():
        path = sam_schema_path(kind, directory)
        with open(path, "w", encoding="utf-8") as file:
            file.write(sam_schema_json(kind))
        paths.append(path)
    for stale in set(glob.glob(os.path.join(directory, f"*{SAM_SCHEMA_SUFFIX}"))) - set(paths):
        os.remove(stale)
    return paths


__all__ = ["sam_models", "sam_schema", "sam_schema_json", "sam_schema_path", "write_sam_schemas"]
