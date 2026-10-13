"""Common Swagger definitions for CLI API views."""

import os
from http import HTTPStatus

from drf_yasg import openapi
from rest_framework import serializers

from smarter.common.const import (
    PROJECT_ROOT,
    SMARTER_BUG_REPORT_URL,
    SMARTER_CUSTOMER_SUPPORT_EMAIL,
)
from smarter.lib import json
from smarter.lib.typing import SmarterDictType

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
    os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "apply", "llmclient.yaml"), encoding="utf-8"
) as f:
    EXAMPLE_MANIFEST_LLM_CLIENT = f.read()

with open(
    os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "prompt", "prompt.json"), encoding="utf-8"
) as f:
    EXAMPLE_CHAT_PROMPT = json.load(f)

with open(
    os.path.join(PROJECT_ROOT, "apps", "api", "v1", "cli", "data", "prompt", "chat_config.json"), encoding="utf-8"
) as f:
    EXAMPLE_CHAT_CONFIG = json.load(f)


# pylint: disable=W0223
class ManifestSerializer(serializers.Serializer):
    """Serializer for the YAML manifest in smarter.sh/v1 format."""

    manifest = serializers.CharField(
        help_text="YAML manifest in smarter.sh/v1 format",
        default=EXAMPLE_MANIFEST_LLM_CLIENT,
    )


class MessageSerializer(serializers.Serializer):
    """Serializer for a message in smarter.sh/v1 format."""

    role = serializers.CharField(help_text="Role of the message sender (system, assistant, user)")
    content = serializers.CharField(help_text="Content of the message")


class CliChatSerializer(serializers.Serializer):
    """The request body of the cli's prompt: smarter.apps.api.v1.contract.models.CliApiPromptBody."""

    prompt = serializers.CharField(help_text="The user's message.")
    session_key = serializers.CharField(
        help_text="Optional. The chat session to continue. By default, the session that the uid used last.",
        required=False,
    )
    messages = serializers.ListSerializer(
        child=MessageSerializer(),
        help_text="Optional. The chat's earlier messages, to which the prompt is added. By default, a new chat.",
        required=False,
    )


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
    "llmclient_name": openapi.Parameter(
        "name", openapi.IN_PATH, description="The LLMClient's name.", type=openapi.TYPE_STRING, required=True
    ),
    "uid": openapi.Parameter(
        "uid",
        openapi.IN_QUERY,
        description=(
            "Required. A unique identifier of the client, e.g. a combination of the machine's MAC address and its "
            "hostname. The platform caches the client's chat session under it, so that the next prompt continues it."
        ),
        type=openapi.TYPE_STRING,
        required=True,
    ),
    "new_session": openapi.Parameter(
        "new_session",
        openapi.IN_QUERY,
        description="Optional. true starts a new chat session, instead of continuing the client's last one.",
        type=openapi.TYPE_STRING,
        enum=["true", "false"],
        default="false",
        required=False,
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


def json_error_response(message: str) -> SmarterDictType:
    """Helper function to generate a JSON error response."""
    return {"status": "error", "message": message}


def json_success_response(message: str) -> SmarterDictType:
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
    "CliChatSerializer",
    "SuccessResponseSerializer",
    "json_success_response",
]
