"""
Common constants for Brokered CLI API views.
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

    uid = serializers.CharField(help_text="Client UID")
    session_key = serializers.CharField(
        help_text="Optional session key. If not provided, a new session key will be generated."
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


def json_error_response(message: str) -> dict:
    """Helper function to generate a JSON error response."""
    return {"status": "error", "message": message}


# @swagger_auto_schema responses
COMMON_SWAGGER_RESPONSES = {
    HTTPStatus.OK: openapi.Response(
        description="Manifest applied successfully",
        examples={"application/json": json_error_response("Manifest applied successfully")},
    ),
    HTTPStatus.BAD_REQUEST: openapi.Response(
        description="Malformed manifest or missing data",
        examples={"application/json": json_error_response("No YAML manifest provided.")},
    ),
    HTTPStatus.FORBIDDEN: openapi.Response(
        description="Forbidden",
        examples={"application/json": json_error_response("You do not have permission to perform this action.")},
    ),
    HTTPStatus.NOT_FOUND: openapi.Response(
        description="Resource not found",
        examples={"application/json": json_error_response("Requested resource not found.")},
    ),
    HTTPStatus.METHOD_NOT_ALLOWED: openapi.Response(
        description="Method not allowed",
        examples={"application/json": json_error_response("HTTP method not allowed on this endpoint.")},
    ),
    HTTPStatus.INTERNAL_SERVER_ERROR: openapi.Response(
        description="Internal server error",
        examples={"application/json": json_error_response("An unexpected error occurred.")},
    ),
    HTTPStatus.NOT_IMPLEMENTED: openapi.Response(
        description="Not implemented",
        examples={"application/json": json_error_response("This feature is not implemented.")},
    ),
    HTTPStatus.SERVICE_UNAVAILABLE: openapi.Response(
        description="Service unavailable",
        examples={"application/json": json_error_response("Service is temporarily unavailable.")},
    ),
}

__all__ = [
    "COMMON_SWAGGER_RESPONSES",
    "COMMON_SWAGGER_PARAMETERS",
    "BUG_REPORT",
    "ManifestSerializer",
    "ChatConfigSerializer",
    "CliChatSerializer",
]
