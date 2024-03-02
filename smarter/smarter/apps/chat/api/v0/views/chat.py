# -*- coding: utf-8 -*-
# pylint: disable=R0801
"""All Django views for the OpenAI Function Calling API app."""
import json
from http import HTTPStatus

import openai
from django.contrib.auth.models import User
from knox.auth import TokenAuthentication
from rest_framework import permissions, viewsets
from rest_framework.authentication import SessionAuthentication
from rest_framework.response import Response

from smarter.apps.chat.functions.function_weather import (
    get_current_weather,
    weather_tool_factory,
)
from smarter.apps.chat.signals import (
    chat_completion_called,
    chat_completion_plugin_selected,
    chat_completion_tool_call_created,
    chat_completion_tool_call_received,
    chat_completion_tools_call,
    chat_invoked,
    chat_response_failure,
    chat_response_success,
)
from smarter.apps.common.conf import settings
from smarter.apps.common.const import VALID_CHAT_COMPLETION_MODELS, OpenAIResponseCodes
from smarter.apps.common.exceptions import EXCEPTION_MAP
from smarter.apps.common.utils import (
    exception_response_factory,
    get_request_body,
    http_response_factory,
    parse_request,
    request_meta_data_factory,
)
from smarter.apps.common.validators import (  # validate_embedding_request,
    validate_completion_request,
    validate_item,
)
from smarter.apps.plugin.plugin import Plugin
from smarter.apps.plugin.utils import plugins_for_user


openai.organization = settings.openai_api_organization
openai.api_key = settings.openai_api_key.get_secret_value()


# pylint: disable=too-many-locals,too-many-statements
def handler(user: User, data: dict):
    """
    Main Lambda handler function.

    Responsible for processing incoming requests and invoking the appropriate
    OpenAI API endpoint based on the contents of the request.
    """
    chat_invoked.send(sender=handler, user=user, data=data)
    weather_tool = weather_tool_factory()
    tools = [weather_tool]
    available_functions = {
        "get_current_weather": get_current_weather,
    }

    try:
        openai_response = {}
        request_body = get_request_body(data=data)
        object_type, model, messages, input_text, temperature, max_tokens = parse_request(request_body)
        request_meta_data = request_meta_data_factory(model, object_type, temperature, max_tokens, input_text)

        # does the prompt have anything to do with any of the search terms defined in a plugin?
        # FIX NOTE: need to decide on how to resolve which of many plugin values sets to use for model, temperature, max_tokens
        for plugin in plugins_for_user(user):
            if plugin.selected(user=user, messages=messages):
                model = plugin.plugin_prompt.model
                temperature = plugin.plugin_prompt.temperature
                max_tokens = plugin.plugin_prompt.max_tokens
                messages = plugin.customize_prompt(messages)
                custom_tool = plugin.custom_tool
                tools.append(custom_tool)
                available_functions[plugin.function_calling_identifier] = plugin.function_calling_plugin
                chat_completion_plugin_selected.send(
                    sender=handler,
                    plugin=plugin.plugin_meta if plugin else None,
                    user=user,
                    data=data,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    custom_tool=custom_tool,
                )

        # https://platform.openai.com/docs/guides/gpt/chat-completions-api
        validate_item(
            item=model,
            valid_items=VALID_CHAT_COMPLETION_MODELS,
            item_type="ChatCompletion models",
        )
        validate_completion_request(request_body)
        chat_completion_called.send(sender=handler, user=user, data=data, action="request")
        openai_response = openai.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        openai_response_dict = json.loads(openai_response.model_dump_json())
        response_message = openai_response.choices[0].message
        chat_completion_called.send(sender=handler, user=user, data=openai_response_dict, action="response")
        openai_response = openai_response.model_dump()
        tool_calls = response_message.tool_calls
        if tool_calls:
            chat_completion_tools_call.send(
                sender=handler,
                user=user,
                model=model,
                tools=tools,
                temperature=temperature,
                max_tokens=max_tokens,
                response=openai_response_dict,
            )
            # Step 3: call the function
            # Note: the JSON response may not always be valid; be sure to handle errors
            messages.append(response_message)  # extend conversation with assistant's reply

            # Step 4: send the info for each function call and function response to the model
            for tool_call in tool_calls:
                plugin: Plugin = None
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)

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
                    function_response = plugin.function_calling_plugin(
                        user=user, inquiry_type=function_args.get("inquiry_type")
                    )
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )  # extend conversation with function response
            chat_completion_tool_call_created.send(
                sender=handler,
                plugin=plugin.plugin_meta if plugin else None,
                user=user,
                data=data,
                model=model,
            )
            second_response = openai.chat.completions.create(
                model=model,
                messages=messages,
            )  # get a new response from the model where it can see the function response
            openai_response = second_response.model_dump()
            openai_response_dict = json.loads(second_response.model_dump_json())
            chat_completion_tool_call_received.send(
                sender=handler,
                plugin=plugin.plugin_meta if plugin else None,
                user=user,
                data=data,
                model=model,
                response=openai_response_dict,
            )

    # handle anything that went wrong
    # pylint: disable=broad-exception-caught
    except Exception as e:
        chat_response_failure.send(sender=handler, user=user, exception=e, data=data)
        status_code, _message = EXCEPTION_MAP.get(type(e), (HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error"))
        return http_response_factory(status_code=status_code, body=exception_response_factory(e))

    def messages_serializer_generator(messages):
        for message in messages:
            if isinstance(message, dict):
                yield message
            else:
                yield message.model_dump()

    serialized_messages = list(messages_serializer_generator(messages))

    # success!! return the response
    chat_response_success.send(
        sender=handler,
        user=user,
        model=model,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
        messages=serialized_messages,
        response=openai_response,
        data=data,
    )
    return http_response_factory(
        status_code=OpenAIResponseCodes.HTTP_RESPONSE_OK,
        body={**openai_response, **request_meta_data},
    )


class FunctionCallingViewSet(viewsets.ViewSet):
    """top-level viewset for openai api function calling"""

    authentication_classes = [TokenAuthentication, SessionAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        """override the create method to handle POST requests."""
        return Response(handler(user=request.user, data=request.data))
