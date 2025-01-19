"""OpenAI API request validators"""

import json

from smarter.common.exceptions import SmarterValueError

from .const import OpenAIEndPoint, OpenAIMessageKeys, OpenAIObjectTypes


####################################################################################################
# Legacy openai validators
####################################################################################################


def validate_temperature(temperature: any) -> None:
    """Ensure that temperature is a float between 0 and 1"""
    try:
        float_temperature = float(temperature)
        if float_temperature < 0 or float_temperature > 1:
            raise SmarterValueError("temperature should be between 0 and 1")
    except SmarterValueError as exc:
        raise SmarterValueError("Temperature must be a float") from exc


def validate_max_tokens(max_tokens: any) -> None:
    """Ensure that max_tokens is an int between 1 and 2048"""
    if not isinstance(max_tokens, int):
        raise TypeError("max_tokens should be an int")

    if max_tokens < 1 or max_tokens > 2048:
        raise SmarterValueError("max_tokens should be between 1 and 2048")


def validate_endpoint(end_point: any) -> None:
    """Ensure that end_point is a valid endpoint based on the OpenAIEndPoint enum"""
    if not isinstance(end_point, str):
        raise TypeError(f"Invalid end_point '{end_point}'. end_point should be a string.")

    if end_point not in OpenAIEndPoint.all_endpoints:
        raise SmarterValueError(f"Invalid end_point {end_point}. Should be one of {OpenAIEndPoint.all_endpoints}")


def validate_object_types(object_type: any) -> None:
    """Ensure that object_type is a valid object type based on the OpenAIObjectTypes enum"""
    if not isinstance(object_type, str):
        raise TypeError(f"Invalid object_type '{object_type}'. object_type should be a string.")

    if object_type not in OpenAIObjectTypes.all_object_types:
        raise SmarterValueError(
            f"Invalid object_type {object_type}. Should be one of {OpenAIObjectTypes.all_object_types}"
        )


def validate_request_body(request_body) -> None:
    """See openai.chat.completion.request.json"""
    if not isinstance(request_body, dict):
        raise TypeError("request body should be a dict")


def validate_messages(request_body):
    """See openai.chat.completion.request.json"""
    if "messages" not in request_body:
        raise SmarterValueError("dict key 'messages' was not found in request body object")
    messages = request_body["messages"]
    if not isinstance(messages, list):
        raise SmarterValueError("dict key 'messages' should be a JSON list")
    for message in messages:
        if not isinstance(message, dict):
            raise SmarterValueError(f"invalid object type {type(message)} found in messages list")
        if "role" not in message:
            raise SmarterValueError(f"dict key 'role' not found in message {json.dumps(message, indent=4)}")
        if message["role"] not in OpenAIMessageKeys.all_roles:
            raise SmarterValueError(
                f"invalid role {message['role']} found in message {json.dumps(message, indent=4)}. "
                f"Should be one of {OpenAIMessageKeys.all_roles}"
            )
        if "content" not in message:
            raise SmarterValueError(f"dict key 'content' not found in message {json.dumps(message, indent=4)}")


def validate_completion_request(request_body, version: str = "v1") -> None:
    """See openai.chat.completion.request.json"""

    validate_request_body(request_body=request_body)
    validate_messages(request_body=request_body)

    if version == "v1":
        if "model" not in request_body:
            raise SmarterValueError("dict key 'model' not found in request body object")
        if "temperature" not in request_body:
            raise SmarterValueError("dict key 'temperature' not found in request body object")
        if "max_tokens" not in request_body:
            raise SmarterValueError("dict key 'max_tokens' not found in request body object")


def validate_embedding_request(request_body) -> None:
    """See openai.embedding.request.json"""
    validate_request_body(request_body=request_body)
    if "input_text" not in request_body:
        raise SmarterValueError("dict key 'input_text' not found in request body object")
