"""Test :func:`smarter.apps.plugin.models.validators.validate_openai_parameters_dict`."""

from smarter.apps.plugin.models.exceptions import PluginDataValueError
from smarter.apps.plugin.models.validators import validate_openai_parameters_dict
from smarter.lib.unittest.base_classes import SmarterTestBase


def parameters(**properties) -> dict:
    return {"type": "object", "properties": properties, "required": list(properties)[:1]}


class TestValidateOpenaiParametersDict(SmarterTestBase):
    """Test that a function's parameters are validated as openai expects them."""

    def test_valid(self):
        valid = parameters(
            name={"type": "string", "description": "a name", "default": "x"},
            count={"type": "number", "description": "a count", "default": 1},
            tags={"type": "array", "description": "tags", "default": []},
            extra={"type": "object", "description": "extra", "default": {}},
            unit={"type": "string", "enum": ["a", "b"], "description": "a unit", "default": None},
        )
        validate_openai_parameters_dict(valid)
        validate_openai_parameters_dict(str(valid))
        self.assertIsNone(validate_openai_parameters_dict(None))

    def test_boolean_type(self):
        """Test that a boolean parameter, whose json schema type is boolean, is valid, and its default is checked."""
        validate_openai_parameters_dict(parameters(flag={"type": "boolean", "description": "a flag", "default": True}))
        with self.assertRaises(PluginDataValueError):
            validate_openai_parameters_dict(
                parameters(flag={"type": "boolean", "description": "a flag", "default": "true"})
            )
        with self.assertRaises(PluginDataValueError):
            validate_openai_parameters_dict(parameters(flag={"type": "bool", "description": "a flag", "default": True}))

    def test_invalid(self):
        """Test each way in which the parameters can be invalid."""
        cases = {
            "not a literal": "{not: valid",
            "not a dict": [1, 2],
            "no properties": {"required": []},
            "no required": {"properties": {}},
            "required not a list": {"properties": {}, "required": "name"},
            "required not a string": {"properties": {}, "required": [1]},
            "required not a property": {"properties": {}, "required": ["name"]},
            "properties not a dict": {"properties": [], "required": []},
            "property not a dict": {"properties": {"name": "string"}, "required": []},
            "invalid key": parameters(name={"type": "string", "description": "d", "format": "x"}),
            "no type": parameters(name={"description": "d"}),
            "invalid type": parameters(name={"type": "date", "description": "d"}),
            "no description": parameters(name={"type": "string"}),
            "string default": parameters(name={"type": "string", "description": "d", "default": 1}),
            "number default": parameters(name={"type": "number", "description": "d", "default": "1"}),
            "array default": parameters(name={"type": "array", "description": "d", "default": "a"}),
            "object default": parameters(name={"type": "object", "description": "d", "default": "a"}),
        }
        for case, value in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(PluginDataValueError):
                    validate_openai_parameters_dict(value)
