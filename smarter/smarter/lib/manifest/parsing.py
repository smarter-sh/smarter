"""
Parse a manifest's text, YAML or JSON, into the dict that its Pydantic model validates.

A manifest arrives as text: a file, a request body, or a string that an extension or a
management command passes on. This module turns that text into a dict, and nothing more.
Whether the dict is a valid manifest, i.e. whether it has an ``apiVersion``, a ``kind``,
``metadata`` and a ``spec`` of the right types, is decided by the kind's Pydantic model.

YAML is a superset of JSON, so one parser reads both.
"""

from typing import Union

import yaml

from smarter.lib.typing import SmarterDictType

from .exceptions import SAMValidationError


def parse_manifest(manifest: Union[str, SmarterDictType]) -> SmarterDictType:
    """
    Parse a manifest's YAML or JSON text into a dict.

    .. code-block:: python

        data = parse_manifest(yaml_text)
        manifest = SAMGuardrail.model_validate(data)

    :param manifest: The manifest, as YAML or JSON text, or as a dict, which is returned as is.
    :returns: The manifest, as a dict.
    :raises SAMValidationError: If the text is not valid YAML, or is not a YAML object, e.g. a
        list or a plain string.
    """
    if isinstance(manifest, dict):
        return manifest
    if not isinstance(manifest, str):
        raise SAMValidationError(f"A manifest must be YAML or JSON text, not a {type(manifest).__name__}.")
    try:
        data = yaml.safe_load(manifest)
    except yaml.YAMLError as e:
        raise SAMValidationError(f"The manifest is not valid YAML or JSON: {e}") from e
    if not isinstance(data, dict):
        raise SAMValidationError(
            f"A manifest must be a YAML object with apiVersion, kind, metadata and spec, not a {type(data).__name__}."
        )
    return data


def read_manifest_file(file_path: str) -> SmarterDictType:
    """
    Read a manifest file, YAML or JSON, into a dict.

    :param file_path: The path of the manifest file.
    :returns: The manifest, as a dict.
    :raises FileNotFoundError: If there is no such file.
    :raises SAMValidationError: If the file is not a YAML or JSON object.
    """
    with open(file_path, encoding="utf-8") as file:
        text = file.read()
    data = parse_manifest(text)
    return data
