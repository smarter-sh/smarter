"""
Find the keys of a manifest that its Pydantic model does not define, e.g. misspellings.

The manifest models ignore keys that they do not define, because brokers also build them from
Django ORM records, whose dicts have other fields. A manifest that a client sends, however,
must not have any: a misspelled key would otherwise be silently ignored. Brokers therefore
check the client's manifest with :func:`unknown_keys` before they use it.
"""

import types
import typing
from typing import Any, Optional, Union

from pydantic import BaseModel


def _models_of(annotation: Any) -> Optional[list[type[BaseModel]]]:
    """
    The Pydantic models of a field's type, e.g. ``Optional[List[Spec]]`` is ``[Spec]``.

    :returns: None if a value of the type may be anything else, e.g. a dict or a str, whose
        keys are therefore not checked.
    """
    if isinstance(annotation, type) and issubclass(annotation, BaseModel):
        return [annotation]
    origin = typing.get_origin(annotation)
    if origin in (Union, types.UnionType):
        models: list[type[BaseModel]] = []
        for arg in typing.get_args(annotation):
            if arg is type(None):
                continue
            arg_models = _models_of(arg)
            if arg_models is None:
                return None
            models.extend(arg_models)
        return models or None
    if origin in (list, tuple, set, frozenset):
        args = [arg for arg in typing.get_args(annotation) if arg is not Ellipsis]
        return _models_of(args[0]) if len(args) == 1 else None
    if origin is typing.Annotated:
        return _models_of(typing.get_args(annotation)[0])
    return None


def _field_names(model: type[BaseModel]) -> dict[str, Any]:
    """The keys that the model accepts, i.e. its field names and aliases, and their types."""
    retval: dict[str, Any] = {}
    for name, field in model.model_fields.items():
        retval[name] = field.annotation
        for alias in (field.alias, field.validation_alias):
            if isinstance(alias, str):
                retval[alias] = field.annotation
    return retval


def unknown_keys(models: Union[type[BaseModel], list[type[BaseModel]]], data: Any, path: str = "") -> list[str]:
    """
    The dotted paths of the keys in the data that none of the models define, e.g. ``spec.config.temperatura``.

    Nested models, including those in lists and Optional fields, are checked too. A value whose
    type is not a model, e.g. a dict of annotations, may have any keys.

    :param models: The Pydantic model of the data, or the models that it may be one of.
    :param data: The manifest, or a part of it.
    :param path: The dotted path of the data in the manifest.
    """
    if isinstance(data, list):
        retval = []
        for index, item in enumerate(data):
            retval.extend(unknown_keys(models, item, f"{path}[{index}]"))
        return retval
    if not isinstance(data, dict):
        return []
    models = models if isinstance(models, list) else [models]
    fields: dict[str, Any] = {}
    for model in models:
        fields.update(_field_names(model))
    retval = []
    for key, value in data.items():
        key_path = f"{path}.{key}" if path else str(key)
        if key not in fields:
            retval.append(key_path)
            continue
        nested = _models_of(fields[key])
        if nested:
            retval.extend(unknown_keys(nested, value, key_path))
    return retval


__all__ = ["unknown_keys"]
