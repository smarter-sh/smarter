"""
Common Swagger definitions for CLI API views.
"""

import json
import os
from http import HTTPStatus

from drf_yasg import openapi
from rest_framework import serializers

from smarter.common.const import (
    PROJECT_ROOT,
    SMARTER_BUG_REPORT_URL,
    SMARTER_CUSTOMER_SUPPORT_EMAIL,
)


with open(os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "get", "plugins.json"), encoding="utf-8") as f:
    EXAMPLE_GET_RESPONSE = json.load(f)

with open(
    os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "describe", "user.json"), encoding="utf-8"
) as f:
    EXAMPLE_DESCRIBE_USER = json.load(f)

with open(
    os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "manifest", "plugin.json"), encoding="utf-8"
) as f:
    EXAMPLE_MANIFEST_PLUGIN = json.load(f)

with open(
    os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "apply", "chatbot.yaml"), encoding="utf-8"
) as f:
    EXAMPLE_MANIFEST_CHATBOT = f.read()

with open(os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "chat", "prompt.json"), encoding="utf-8") as f:
    EXAMPLE_CHAT_PROMPT = json.load(f)

with open(
    os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "chat", "chat_config.json"), encoding="utf-8"
) as f:
    EXAMPLE_CHAT_CONFIG = json.load(f)


# pylint: disable=W0223
class ManifestSerializer(serializers.Serializer):
    """Serializer for the YAML manifest in smarter.sh/v1 format."""

    manifest = serializers.CharField(
        help_text="YAML manifest in smarter.sh/v1 format",
        default=EXAMPLE_MANIFEST_CHATBOT,
    )


class ChatConfigSerializer(serializers.Serializer):
    """Serializer for the chat configuration in smarter.sh/v1 format."""

    uid = serializers.RegexField(
        help_text="Client UID",
        max_length=64,
        min_length=64,
        regex=r"^[0-9a-f]{64}$",
        required=True,
    )
    session_key = serializers.RegexField(
        help_text="Optional session key. If not provided, a new session key will be generated.",
        max_length=64,
        min_length=64,
        regex=r"^[0-9a-f]{64}$",
        required=False,
    )


class MessageSerializer(serializers.Serializer):
    """Serializer for a message in smarter.sh/v1 format."""

    role = serializers.CharField(help_text="Role of the message sender (system, assistant, user)")
    content = serializers.CharField(help_text="Content of the message")


class CliChatSerializer(serializers.Serializer):
    """Serializer for the chat in smarter.sh/v1 format."""

    session_key = serializers.CharField(help_text="Session key for the chat session")
    messages = serializers.ListSerializer(child=MessageSerializer(), help_text="List of chat messages")


BUG_REPORT = (
    "Encountered an unexpected error. "
    f"This is a bug. Please contact {SMARTER_CUSTOMER_SUPPORT_EMAIL} "
    f"and/or report to {SMARTER_BUG_REPORT_URL}."
)

# @swagger_auto_schema manual_parameters
COMMON_SWAGGER_PARAMETERS = {
    "kind": openapi.Parameter(
        "kind", openapi.IN_PATH, description="The kind of resource to delete.", type=openapi.TYPE_STRING, required=True
    ),
    "name": openapi.Parameter(
        "name",
        openapi.IN_PATH,
        description="The name of the resource to delete.",
        type=openapi.TYPE_STRING,
        required=True,
    ),
    "name_query_param": openapi.Parameter(
        "name", openapi.IN_QUERY, description="The name of the resource.", type=openapi.TYPE_STRING, required=True
    ),
}


class ErrorResponseSerializer(serializers.Serializer):
    """Serializer for a JSON error response."""

    status = serializers.CharField(default="error")
    message = serializers.CharField()


class ResponseMetadataSerializer(serializers.Serializer):
    """Serializer for the metadata in the response."""

    count = serializers.IntegerField(required=False)
    command = serializers.CharField(required=False)


class ResponseKwargsSerializer(serializers.Serializer):
    """Serializer for the kwargs in the response."""

    asc = serializers.CharField()
    desc = serializers.CharField()
    i = serializers.CharField()
    username = serializers.CharField()


class ResponseDataSerializer(serializers.Serializer):
    """Serializer for the data in the response."""

    apiVersion = serializers.CharField()
    kind = serializers.CharField()
    metadata = ResponseMetadataSerializer(required=False)
    kwargs = ResponseKwargsSerializer(required=False)
    data = serializers.DictField(required=False)


class SuccessResponseSerializer(serializers.Serializer):
    """Serializer for a JSON success response."""

    data = ResponseDataSerializer()
    message = serializers.CharField()
    api = serializers.CharField()
    thing = serializers.CharField()
    metadata = ResponseMetadataSerializer(required=False)


def json_error_response(message: str) -> dict:
    """Helper function to generate a JSON error response."""
    return {"status": "error", "message": message}


def json_success_response(message: str) -> dict:
    """Helper function to generate a JSON success response."""
    return {
        "application/json": {
            "data": {},
            "message": message,
            "api": "smarter.sh/v1",
            "thing": "User",
            "metadata": {"command": "get"},
        }
    }


def openai_success_response(message: str) -> openapi.Response:
    """Helper function to generate a JSON success response."""
    return openapi.Response(
        description=message,
        examples=json_success_response(message),
        schema=SuccessResponseSerializer(),
    )


# @swagger_auto_schema responses
COMMON_SWAGGER_RESPONSES = {
    HTTPStatus.OK: openai_success_response("Manifest applied successfully"),
    HTTPStatus.BAD_REQUEST: openapi.Response(
        description="Malformed manifest or missing data",
        examples={"application/json": json_error_response("No YAML manifest provided.")},
        schema=ErrorResponseSerializer(),
    ),
    HTTPStatus.FORBIDDEN: openapi.Response(
        description="Forbidden",
        examples={"application/json": json_error_response("You do not have permission to perform this action.")},
        schema=ErrorResponseSerializer(),
    ),
    HTTPStatus.NOT_FOUND: openapi.Response(
        description="Resource not found",
        examples={"application/json": json_error_response("Requested resource not found.")},
        schema=ErrorResponseSerializer(),
    ),
    HTTPStatus.METHOD_NOT_ALLOWED: openapi.Response(
        description="Method not allowed",
        examples={"application/json": json_error_response("HTTP method not allowed on this endpoint.")},
        schema=ErrorResponseSerializer(),
    ),
    HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(
        description="Internal server error",
        examples={"application/json": json_error_response("An unexpected error occurred.")},
        schema=ErrorResponseSerializer(),
    ),
    HTTPStatus.NOT_IMPLEMENTED: openapi.Response(
        description="Not implemented",
        examples={"application/json": json_error_response("This feature is not implemented.")},
        schema=ErrorResponseSerializer(),
    ),
    HTTPStatus.SERVICE_UNAVAILABLE: openapi.Response(
        description="Service unavailable",
        examples={"application/json": json_error_response("Service is temporarily unavailable.")},
        schema=ErrorResponseSerializer(),
    ),
}

__all__ = [
    "COMMON_SWAGGER_RESPONSES",
    "COMMON_SWAGGER_PARAMETERS",
    "BUG_REPORT",
    "ManifestSerializer",
    "ChatConfigSerializer",
    "CliChatSerializer",
    "SuccessResponseSerializer",
    "json_success_response",
]
