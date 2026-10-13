"""Test :mod:`smarter.apps.api.v1.contract.models`."""

from pydantic import ValidationError

from smarter.apps.api.v1.contract.models import (
    CliApiValidation,
    OpenApiMediaType,
    OpenApiParameter,
    OpenApiResponse,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestCliApiModels(SmarterTestBase):
    """Test the models of the cli api's response data."""

    def test_validation(self):
        validation = CliApiValidation.model_validate(
            {"valid": False, "errors": [{"loc": ["spec", 0], "message": "Field required", "type": "missing"}]}
        )
        self.assertEqual(validation.errors[0].loc, ["spec", 0])

    def test_extra_fields_are_allowed(self):
        validation = CliApiValidation.model_validate({"valid": True, "errors": [], "warnings": []})
        self.assertEqual(validation.model_dump()["warnings"], [])


class TestOpenApiModels(SmarterTestBase):
    """Test the models of the OpenAPI document."""

    def test_aliases(self):
        parameter = OpenApiParameter(name="kind", in_="path", required=True, schema_={"type": "string"})
        self.assertEqual(
            parameter.model_dump(mode="json"),
            {"name": "kind", "in": "path", "required": True, "schema": {"type": "string"}},
        )
        self.assertEqual(OpenApiParameter.model_validate(parameter.model_dump(mode="json")), parameter)

    def test_none_fields_are_left_out_but_nulls_in_schemas_are_kept(self):
        response = OpenApiResponse(
            description="Success.",
            content={"application/json": OpenApiMediaType(schema_={"type": "string", "default": None})},
        )
        self.assertEqual(
            response.model_dump(mode="json"),
            {
                "description": "Success.",
                "content": {"application/json": {"schema": {"type": "string", "default": None}}},
            },
        )
        self.assertNotIn("content", OpenApiResponse(description="No content.").model_dump(mode="json"))

    def test_extra_fields_are_forbidden(self):
        with self.assertRaises(ValidationError):
            OpenApiResponse.model_validate({"description": "Success.", "contents": {}})
