# pylint: disable=duplicate-code
# pylint: disable=E1101
"""Utility functions for the OpenAI Lambda functions"""
import base64
import json  # library for interacting with JSON data https://www.json.org/json-en.html
import logging
import sys  # libraries for error management
import traceback  # libraries for error management

from smarter.common.conf import settings as smarter_settings
from smarter.common.const import LANGCHAIN_MESSAGE_HISTORY_ROLES, OpenAIMessageKeys
from smarter.common.exceptions import SmarterValueError
from smarter.common.utils import DateTimeEncoder

from .validators import (
    validate_endpoint,
    validate_max_tokens,
    validate_messages,
    validate_object_types,
    validate_request_body,
    validate_temperature,
)


logger = logging.getLogger(__name__)


def http_response_factory(status_code: int, body, debug_mode: bool = False) -> json:
    """
    Generate a standardized JSON return dictionary for all possible response scenarios.

    status_code: an HTTP response code. see https://developer.mozilla.org/en-US/docs/Web/HTTP/Status
    body: a JSON dict of http response for status 200, an error dict otherwise.

    see https://docs.aws.amazon.com/lambda/latest/dg/python-handler.html
    """
    if status_code < 100 or status_code > 599:
        raise SmarterValueError(f"Invalid HTTP response code received: {status_code}")

    retval = {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "headers": {"Content-Type": "application/json"},
    }

    if status_code != 200:
        logger.error("Error: %s", body)
        return retval

    if debug_mode:
        retval["body"] = body
        # log our output to the CloudWatch log for this Lambda
        logger.info(json.dumps({"retval": retval}, cls=DateTimeEncoder))

    # see https://docs.aws.amazon.com/apigateway/latest/developerguide/http-api-develop-integrations-lambda.html
    retval["body"] = json.dumps(body, cls=DateTimeEncoder)

    return retval


def exception_response_factory(exception, request_meta_data: dict = None) -> json:
    """
    Generate a standardized error response dictionary that includes
    the Python exception type and stack trace.

    exception: a descendant of Python Exception class
    """

    exc_info = sys.exc_info()
    retval = {
        "request_meta_data": request_meta_data,
        "error": str(exception),
        "description": "".join(traceback.format_exception(*exc_info)),
    }

    return retval


def get_request_body(data) -> dict:
    """
    Returns the request body as a dictionary.

    Args:
        event: The event object containing the request body.

    Returns:
        A dictionary representing the request body.
    """
    if hasattr(data, "isBase64Encoded") and bool(data["isBase64Encoded"]):
        # pylint: disable=line-too-long
        #  https://stackoverflow.com/questions/9942594/unicodeencodeerror-ascii-codec-cant-encode-character-u-xa0-in-position-20
        #  https://stackoverflow.com/questions/53340627/typeerror-expected-bytes-like-object-not-str
        request_body = str(data["body"]).encode("ascii")
        request_body = base64.b64decode(request_body)
    else:
        request_body = data

    validate_request_body(request_body=request_body)

    if hasattr(request_body, "temperature"):
        temperature = request_body["temperature"]
        validate_temperature(temperature=temperature)

    if hasattr(request_body, "max_tokens"):
        max_tokens = request_body["max_tokens"]
        validate_max_tokens(max_tokens=max_tokens)

    if hasattr(request_body, "end_point"):
        end_point = request_body["end_point"]
        validate_endpoint(end_point=end_point)

    if hasattr(request_body, "object_type"):
        object_type = request_body["object_type"]
        validate_object_types(object_type=object_type)

    validate_messages(request_body=request_body)
    return request_body


def parse_request(request_body: dict):
    """Parse the request body and return the endpoint, model, messages, and input_text"""
    messages = request_body.get("messages")
    input_text = request_body.get("input_text")
    chat_history = request_body.get("chat_history")

    if not messages and not input_text:
        raise SmarterValueError("A value for either messages or input_text is required")

    if chat_history and input_text:
        # memory-enabled request assumed to be destined for langchain_passthrough
        # we'll need to rebuild the messages list from the chat_history
        messages = []
        for chat in chat_history:
            messages.append({"role": chat["sender"], "content": chat["message"]})
        messages.append({"role": "user", "content": input_text})

    if not input_text:
        # we need to extract the most recent prompt for the user role
        input_text = get_content_for_role(messages, "user")

    return messages, input_text


def get_content_for_role(messages: list, role: str) -> str:
    """Get the text content from the messages list for a given role"""
    retval = [d.get("content") for d in messages if d["role"] == role]
    try:
        return retval[-1]
    except IndexError:
        return ""


def get_message_history(messages: list) -> list:
    """Get the text content from the messages list for a given role"""
    message_history = [
        {"role": d["role"], "content": d.get("content")}
        for d in messages
        if d["role"] in LANGCHAIN_MESSAGE_HISTORY_ROLES
    ]
    return message_history


def get_messages_for_role(messages: list, role: str) -> list:
    """Get the text content from the messages list for a given role"""
    retval = [d.get("content") for d in messages if d["role"] == role]
    return retval


def request_meta_data_factory(model, temperature, max_tokens, input_text):
    """
    Return a dictionary of request meta data.
    """
    return {
        "model": model,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "input_text": input_text,
    }


def ensure_system_role_present(
    messages: list[dict], default_system_role: str = smarter_settings.openai_default_system_role
) -> list:
    """
    Ensure that a system role is present in the messages list
    """
    if not any(
        d[OpenAIMessageKeys.OPENAI_MESSAGE_ROLE_KEY] == OpenAIMessageKeys.OPENAI_SYSTEM_MESSAGE_KEY for d in messages
    ):
        logger.warning("No system role found in messages list, adding default system role")
        messages.insert(
            0,
            {
                OpenAIMessageKeys.OPENAI_MESSAGE_ROLE_KEY: OpenAIMessageKeys.OPENAI_SYSTEM_MESSAGE_KEY,
                OpenAIMessageKeys.OPENAI_MESSAGE_CONTENT_KEY: default_system_role,
            },
        )
    return messages
