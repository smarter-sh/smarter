# -*- coding: utf-8 -*-
# pylint: disable=R0801
"""All Django views for the OpenAI Function Calling API app."""
import json

import openai
from django.contrib.auth.models import User
from rest_framework import permissions, viewsets
from rest_framework.response import Response

from smarter.apps.chat.signals import (
    chat_completion_called,
    chat_completion_failed,
    chat_completion_returned,
    chat_completion_tool_call_created,
    chat_completion_tool_call_received,
    chat_invoked,
    plugin_selected,
)
from smarter.apps.common.conf import settings
from smarter.apps.common.const import VALID_CHAT_COMPLETION_MODELS, OpenAIResponseCodes
from smarter.apps.common.exceptions import EXCEPTION_MAP
from smarter.apps.common.utils import (
    exception_response_factory,
    get_logger,
    get_request_body,
    http_response_factory,
    parse_request,
    request_meta_data_factory,
)
from smarter.apps.common.validators import (  # validate_embedding_request,
    validate_completion_request,
    validate_item,
)

# OpenAI functions
from smarter.apps.plugin.utils import plugins_for_user

from .function_weather import get_current_weather, weather_tool_factory
from .utils import (
    customized_prompt,
    function_calling_plugin,
    plugin_tool_factory,
    search_terms_are_in_messages,
)


logger = get_logger(__name__)
openai.organization = settings.openai_api_organization
openai.api_key = settings.openai_api_key.get_secret_value()


# pylint: disable=too-many-locals
def handler(user: User, data: dict):
    """
    Main Lambda handler function.

    Responsible for processing incoming requests and invoking the appropriate
    OpenAI API endpoint based on the contents of the request.
    """
    chat_invoked.send(sender=handler, user=user, data=data)
    weather_tool = weather_tool_factory()
    tools = [weather_tool]

    try:
        openai_results = {}
        request_body = get_request_body(data=data)
        object_type, model, messages, input_text, temperature, max_tokens = parse_request(request_body)
        request_meta_data = request_meta_data_factory(model, object_type, temperature, max_tokens, input_text)

        # does the prompt have anything to do with any of the search terms defined in a plugin?
        # FIX NOTE: need to decide on how to resolve which of many plugin values sets to use for model, temperature, max_tokens
        for plugin in plugins_for_user(user):
            if search_terms_are_in_messages(messages=messages, search_terms=plugin.plugin_selector.search_terms):
                model = plugin.plugin_prompt.model
                temperature = plugin.plugin_prompt.temperature
                max_tokens = plugin.plugin_prompt.max_tokens
                messages = customized_prompt(plugin=plugin, messages=messages)
                custom_tool = plugin_tool_factory(plugin=plugin)
                tools.append(custom_tool)
                plugin_selected.send(
                    sender=handler,
                    plugin=plugin,
                    user=user,
                    data=data,
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    messages=messages,
                    tools=tools,
                    custom_tool=custom_tool,
                    input_text=input_text,
                )
                print(
                    f"Adding plugin: {plugin.name} {plugin.plugin_meta.version} created by {plugin.plugin_meta.author.user.username}"
                )

        # https://platform.openai.com/docs/guides/gpt/chat-completions-api
        validate_item(
            item=model,
            valid_items=VALID_CHAT_COMPLETION_MODELS,
            item_type="ChatCompletion models",
        )
        validate_completion_request(request_body)
        chat_completion_called.send(sender=handler, user=user, data=data)
        openai_results = openai.chat.completions.create(
            model=model,
            messages=messages,
            tools=tools,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        response_message = openai_results.choices[0].message
        openai_results = openai_results.model_dump()
        tool_calls = response_message.tool_calls
        if tool_calls:
            # Step 3: call the function
            # Note: the JSON response may not always be valid; be sure to handle errors
            available_functions = {
                "get_current_weather": get_current_weather,
                "function_calling_plugin": function_calling_plugin,
            }  # only one function in this example, but you can have multiple
            messages.append(response_message)  # extend conversation with assistant's reply
            # Step 4: send the info for each function call and function response to the model
            for tool_call in tool_calls:
                function_name = tool_call.function.name
                function_to_call = available_functions[function_name]
                function_args = json.loads(tool_call.function.arguments)

                if function_name == "get_current_weather":
                    function_response = function_to_call(
                        location=function_args.get("location"),
                        unit=function_args.get("unit"),
                    )
                elif function_name == "function_calling_plugin":
                    function_response = function_to_call(user=user, inquiry_type=function_args.get("inquiry_type"))
                messages.append(
                    {
                        "tool_call_id": tool_call.id,
                        "role": "tool",
                        "name": function_name,
                        "content": function_response,
                    }
                )  # extend conversation with function response
            chat_completion_tool_call_created.send(
                sender=handler, user=user, data=data, input_text=input_text, messages=messages, model=model
            )
            second_response = openai.chat.completions.create(
                model=model,
                messages=messages,
            )  # get a new response from the model where it can see the function response
            openai_results = second_response.model_dump()
            chat_completion_tool_call_received.send(
                sender=handler,
                user=user,
                data=data,
                input_text=input_text,
                messages=messages,
                model=model,
                response=openai_results,
            )

    # handle anything that went wrong
    # pylint: disable=broad-exception-caught
    except Exception as e:
        chat_completion_failed.send(sender=handler, user=user, exception=e, data=data)
        status_code, _message = EXCEPTION_MAP.get(type(e), (500, "Internal server error"))
        return http_response_factory(status_code=status_code, body=exception_response_factory(e))

    # success!! return the results
    chat_completion_returned.send(
        sender=handler,
        user=user,
        input_text=input_text,
        model=model,
        messages=messages,
        tools=tools,
        temperature=temperature,
        max_tokens=max_tokens,
        results=openai_results,
        data=data,
    )
    return http_response_factory(
        status_code=OpenAIResponseCodes.HTTP_RESPONSE_OK,
        body={**openai_results, **request_meta_data},
    )


class FunctionCallingViewSet(viewsets.ViewSet):
    """top-level viewset for openai api function calling"""

    permission_classes = [permissions.IsAuthenticated]

    def create(self, request):
        """override the create method to handle POST requests."""
        return Response(handler(user=request.user, data=request.data))
