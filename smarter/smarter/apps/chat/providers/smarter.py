# pylint: disable=R0801
"""All Django views for the OpenAI Function Calling API app."""
import json
import logging
from http import HTTPStatus
from typing import List

import openai

from smarter.apps.account.tasks import (
    create_plugin_charge,
    create_prompt_completion_charge,
)
from smarter.apps.chat.functions.function_weather import (
    get_current_weather,
    weather_tool_factory,
)
from smarter.apps.chat.models import Chat
from smarter.apps.chat.signals import (
    chat_completion_called,
    chat_completion_plugin_selected,
    chat_completion_tool_call_created,
    chat_invoked,
    chat_response_failure,
    chat_response_success,
)
from smarter.apps.plugin.api.v0.serializers import PluginMetaSerializer
from smarter.apps.plugin.plugin import Plugin
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import VALID_CHAT_COMPLETION_MODELS
from smarter.common.exceptions import EXCEPTION_MAP
from smarter.lib.django.user import UserType

from .utils import (
    exception_response_factory,
    get_request_body,
    http_response_factory,
    parse_request,
    request_meta_data_factory,
)
from .validators import validate_completion_request, validate_item


logger = logging.getLogger(__name__)
openai.organization = smarter_settings.openai_api_organization
openai.api_key = smarter_settings.openai_api_key.get_secret_value()


# pylint: disable=too-many-locals,too-many-statements,too-many-arguments
def handler(
    chat: Chat,
    data: dict,
    plugins: List[Plugin] = None,
    user: UserType = None,
    default_model: str = smarter_settings.openai_default_model,
    default_temperature: float = smarter_settings.openai_default_temperature,
    default_max_tokens: int = smarter_settings.openai_default_max_tokens,
):
    """
    Chat prompt handler. Responsible for processing incoming requests and
    invoking the appropriate OpenAI API endpoint based on the contents of
    the request.
    """
    request_meta_data: dict = None
    first_iteration = {}
    first_response = {}
    second_iteration = {}
    first_response_dict: dict = None
    second_response_dict: dict = None
    messages: list[dict] = None
    input_text: str = None

    weather_tool = weather_tool_factory()
    tools = [weather_tool]
    available_functions = {
        "get_current_weather": get_current_weather,
    }

    try:
        request_body = get_request_body(data=data)
        messages, input_text = parse_request(request_body)
        model = default_model
        temperature = default_temperature
        max_tokens = default_max_tokens
        request_meta_data = request_meta_data_factory(model, temperature, max_tokens, input_text)
        chat_invoked.send(sender=handler, chat=chat, data=data)

        # does the prompt have anything to do with any of the search terms defined in a plugin?
        # FIX NOTE: need to decide on how to resolve which of many plugin values sets to use for model, temperature, max_tokens
        logger.warning(
            "smarter.apps.chat.providers.smarter.handler(): plugins selector needs to be refactored to use Django model."
        )
        for plugin in plugins:
            if plugin.selected(user=user, input_text=input_text):
                model = plugin.plugin_prompt.model
                temperature = plugin.plugin_prompt.temperature
                max_tokens = plugin.plugin_prompt.max_tokens
                messages = plugin.customize_prompt(messages)
                custom_tool = plugin.custom_tool
                tools.append(custom_tool)
                available_functions[plugin.function_calling_identifier] = plugin.function_calling_plugin
                chat_completion_plugin_selected.send(
                    sender=handler, chat=chat, plugin=plugin.plugin_meta, input_text=input_text
                )

        # https://platform.openai.com/docs/guides/gpt/chat-completions-api
        validate_item(
            item=model,
            valid_items=VALID_CHAT_COMPLETION_MODELS,
            item_type="ChatCompletion models",
        )
        validate_completion_request(request_body, version="v1")
        first_iteration["request"] = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        first_response = openai.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        first_response_dict = json.loads(first_response.model_dump_json())
        first_iteration["response"] = first_response_dict
        chat_completion_called.send(
            sender=handler,
            chat=chat,
            iteration=1,
            request=first_iteration["request"],
            response=first_iteration["response"],
        )
        create_prompt_completion_charge(
            handler.__name__,
            user.id,
            model,
            first_response.usage.completion_tokens,
            first_response.usage.prompt_tokens,
            first_response.usage.total_tokens,
            first_response.system_fingerprint,
        )
        response_message = first_response.choices[0].message
        tool_calls = response_message.tool_calls
        if tool_calls:
            modified_messages = messages.copy()
            # this is intended to force a json serialization exception
            # in the event that we've neglected to properly serialize all
            # responses from openai api.
            response_message_dict = response_message.model_dump_json()
            serialized_messages: list = json.loads(json.dumps(modified_messages))
            serialized_messages.append(response_message_dict)
            serialized_tool_calls = []

            # Step 3: call the function
            # Note: the JSON response may not always be valid; be sure to handle errors
            modified_messages.append(response_message)  # extend conversation with assistant's reply

            # Step 4: send the info for each function call and function response to the model

            for tool_call in tool_calls:
                serialized_tool_call = {}
                plugin: Plugin = None
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)
                serialized_tool_call["function_name"] = function_name
                serialized_tool_call["function_args"] = function_args

                if function_name == "get_current_weather":
                    function_response = function_to_call(
                        location=function_args.get("location"),
                        unit=function_args.get("unit"),
                    )
                elif function_name.startswith("function_calling_plugin"):
                    # FIX NOTE: we should revisit this. technically, we're supposed to be calling
                    # function_to_call, assigned above. but just to play it safe,
                    # we're directly invoking the plugin's function_calling_plugin() method.
                    plugin_id = int(function_name[-4:])
                    plugin = Plugin(plugin_id=plugin_id)
                    function_response = plugin.function_calling_plugin(inquiry_type=function_args.get("inquiry_type"))
                    serialized_tool_call["smarter_plugin"] = PluginMetaSerializer(plugin.plugin_meta).data
                tool_call_message = {
                    "tool_call_id": tool_call.id,
                    "role": "tool",
                    "name": function_name,
                    "content": function_response,
                }
                modified_messages.append(tool_call_message)  # extend conversation with function response
                serialized_messages.append(tool_call_message)
                serialized_tool_calls.append(serialized_tool_call)

            second_iteration["request"] = {
                "model": model,
                "messages": serialized_messages,
            }
            chat_completion_called.send(sender=handler, chat=chat, iteration=2, request=second_iteration["request"])
            second_response = openai.chat.completions.create(
                model=model,
                messages=modified_messages,
            )  # get a new response from the model where it can see the function response
            second_response_dict = json.loads(second_response.model_dump_json())
            second_iteration["response"] = second_response_dict
            second_iteration["request"]["messages"] = serialized_messages
            chat_completion_tool_call_created.send(
                sender=handler,
                chat=chat,
                tool_calls=serialized_tool_calls,
                request=second_iteration["request"],
                response=second_iteration["response"],
            )
            create_plugin_charge(
                handler.__name__,
                user.id,
                model,
                second_response.usage.completion_tokens,
                second_response.usage.prompt_tokens,
                second_response.usage.total_tokens,
                second_response.system_fingerprint,
            )

    # handle anything that went wrong
    # pylint: disable=broad-exception-caught
    except Exception as e:
        chat_response_failure.send(sender=handler, chat=chat, request_meta_data=request_meta_data, exception=e)
        status_code, _message = EXCEPTION_MAP.get(type(e), (HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"))
        return http_response_factory(
            status_code=status_code, body=exception_response_factory(exception=e, request_meta_data=request_meta_data)
        )

    # success!! return the response
    response = second_iteration.get("response") or first_iteration.get("response")
    response["meta_data"] = {"tool_calls": serialized_tool_calls, **request_meta_data}
    chat_response_success.send(sender=handler, chat=chat, request=first_iteration.get("request"), response=response)
    return http_response_factory(status_code=HTTPStatus.OK, body=response)
