"""
Test helpers that validate real responses against the Smarter api's OpenAPI document.

Every family's tests use them: :mod:`smarter.apps.api.v1.contract.tests.test_openapi`, and the
contract tests of an app whose fixtures live with the app, e.g. the vectorstores'.
"""

import functools
import json

from jsonschema import Draft202012Validator
from referencing import Registry, Resource
from referencing.jsonschema import DRAFT202012

from smarter.apps.api.v1.contract.const import OPENAPI_PATH
from smarter.apps.api.v1.contract.openapi import openapi_document
from smarter.lib.typing import SmarterDictType

DOCUMENT_URI = "urn:smarter:openapi"
"""The uri under which the committed document is registered, so that its ``$ref``s resolve."""


def committed_document() -> SmarterDictType:
    """The committed ``openapi.json``."""
    with open(OPENAPI_PATH, encoding="utf-8") as file:
        return json.load(file)


@functools.cache
def document_registry() -> Registry:
    """A JSON Schema registry that holds the committed document."""
    return Registry().with_resource(
        DOCUMENT_URI, Resource.from_contents(committed_document(), default_specification=DRAFT202012)
    )


class OpenApiResponseMixin:
    """Assertions that a body is valid under one of the document's schemas, or under an operation's response."""

    def _errors(self, schema: SmarterDictType, body) -> list[str]:
        schema = json.loads(json.dumps(schema).replace('"#/components/', f'"{DOCUMENT_URI}#/components/'))
        validator = Draft202012Validator(schema, registry=document_registry())
        return [f"{list(error.absolute_path)}: {error.message[:300]}" for error in validator.iter_errors(body)]

    def assertValid(self, schema_name: str, body):  # pylint: disable=invalid-name
        """Assert that a body is valid under one of the document's schemas, by its name."""
        errors = self._errors({"$ref": f"#/components/schemas/{schema_name}"}, body)
        self.assertEqual(errors, [], f"{schema_name}: {str(body)[:500]}")  # type: ignore[attr-defined]

    def assertValidResponse(self, path: str, method: str, body, status: int = 200):  # pylint: disable=invalid-name
        """Assert that a response body is valid under the schema that the document gives its operation and status."""
        operation = getattr(openapi_document().paths[path], method)
        response = operation.responses.get(str(status)) or operation.responses["default"]
        errors = self._errors(response.content["application/json"].schema_, body)
        self.assertEqual(errors, [], f"{method.upper()} {path} {status}: {str(body)[:500]}")  # type: ignore[attr-defined]


__all__ = ["DOCUMENT_URI", "OpenApiResponseMixin", "committed_document", "document_registry"]
