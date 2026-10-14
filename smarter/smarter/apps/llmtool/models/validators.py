"""PluginMeta app models."""

import ast

from .exceptions import PluginDataValueError


def validate_openai_parameters_dict(value):
    """
    Validates that the provided value is a dictionary matching the OpenAI parameters schema.

    **Example schema:**

    .. code-block:: python

        {
            'type': 'object',
            'properties': {
                'max_cost': {
                    'type': 'float',
                    'description': 'the maximum cost that a student is willing to pay for a course.'
                },
                'description': {
                    'type': 'string',
                    'description': 'areas of specialization for courses in the catalogue.',
                    'enum': ['AI', 'mobile', 'web', 'database', 'network', 'neural networks']
                }
            },
            'required': ['max_cost'],
            'additionalProperties': False
        }

    :param value: The value to validate. Should be a dict or a string representation of a dict.
    :raises PluginDataValueError: If the value is not a valid parameters dictionary.
    """
    # pylint: disable=C0415
    from .plugin_data_sql import PluginDataSql

    if value is None:
        return None
    if isinstance(value, str):
        try:
            value = ast.literal_eval(value)
        except (SyntaxError, ValueError) as e:
            raise PluginDataValueError(f"This field must be a valid dict. received: {value}") from e

    if not isinstance(value, dict):
        raise PluginDataValueError(f"This field must contain valid dicts. received: {value}")

    # validations
    if not isinstance(value, dict):
        raise PluginDataValueError("data parameters must be a dictionary.")
    if "properties" not in value.keys():
        raise PluginDataValueError("data parameters missing 'properties' key.")
    if "required" not in value.keys():
        raise PluginDataValueError("data parameters missing 'required' key.")
    else:
        if not isinstance(value["required"], list):
            raise PluginDataValueError("data parameters 'required' must be a list.")
        for item in value["required"]:
            if not isinstance(item, str):
                raise PluginDataValueError("data parameters 'required' items must be strings.")
            if not value["properties"].get(item):
                raise PluginDataValueError(
                    f"data parameters 'required' item '{item}' does not exist as a 'properties' dict."
                )

    # validate each property
    properties = value.get("properties", {})
    if not isinstance(properties, dict):
        raise PluginDataValueError("data parameters 'properties' must be a dictionary.")

    for key, value in properties.items():

        if not isinstance(key, str):
            raise PluginDataValueError("data parameters 'properties' keys must be strings.")
        if not isinstance(value, dict):
            raise PluginDataValueError(f"data parameters 'properties' value for key '{key}' must be a dictionary.")

        for k, _ in value.items():
            valid_keys = ["type", "enum", "description", "default"]
            if k not in valid_keys:
                raise PluginDataValueError(
                    f"data parameters 'properties' key '{k}' is not a valid key. Valid keys are: {valid_keys}"
                )

        if "type" not in value:
            raise PluginDataValueError(f"data parameters 'properties' value for key '{key}' missing 'type' key.")
        if value["type"] not in PluginDataSql.DataTypes.all():
            raise PluginDataValueError(
                f"data parameters 'properties' value for key '{key}' invalid 'type': {value['type']}"
            )
        if "description" not in value:
            raise PluginDataValueError(f"data parameters 'properties' value for key '{key}' missing 'description' key.")
        if "default" in value and value["default"] is not None:
            if value["type"] == "string" and not isinstance(value["default"], str):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be a string."
                )
            if value["type"] == "number" and not isinstance(value["default"], (int, float)):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be a number."
                )
            if value["type"] == "boolean" and not isinstance(value["default"], bool):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be a boolean."
                )
            if value["type"] == "array" and not isinstance(value["default"], list):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be an array."
                )
            if value["type"] == "object" and not isinstance(value["default"], dict):
                raise PluginDataValueError(
                    f"data parameters 'properties' value for key '{key}' 'default' must be an object."
                )
