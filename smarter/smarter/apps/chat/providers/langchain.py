# pylint: disable=R0801
"""
Django view for LanchChain Function Calling API. Supported LLM models: Anthropic, Cohere, Google, Mistral, OpenAI

see:
 - https://python.langchain.com/v0.1/docs/modules/model_io/chat/function_calling/
 - https://python.langchain.com/v0.1/docs/modules/tools/custom_tools/

"""
import json
import logging
from http import HTTPStatus
from typing import Any, Dict, List, Optional

# FIX NOTE: DELETE ME!
import openai
from langchain_core import exceptions as langchain_exceptions
from langchain_core.messages.ai import AIMessage, UsageMetadata
from langchain_core.messages.tool import InvalidToolCall, ToolCall

from smarter.apps.account.tasks import (
    create_plugin_charge,
    create_prompt_completion_charge,
)
from smarter.apps.chat.functions.function_weather import (
    get_current_weather,
    weather_tool_factory,
)
from smarter.apps.chat.models import Chat
from smarter.apps.chat.providers.utils import (
    ensure_system_role_present,
    exception_response_factory,
    get_request_body,
    http_response_factory,
    parse_request,
    request_meta_data_factory,
)
from smarter.apps.chat.providers.validators import validate_item
from smarter.apps.chat.signals import (
    chat_completion_called,
    chat_completion_invalid_tool_call,
    chat_completion_plugin_selected,
    chat_completion_tool_call_created,
    chat_invoked,
    chat_response_failure,
    chat_response_success,
)
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.common.const import SmarterLLMDefaults
from smarter.common.exceptions import (
    SmarterConfigurationError,
    SmarterIlligalInvocationError,
    SmarterValueError,
)
from smarter.lib.django.user import UserType
from smarter.services.llm import llm_vendors


logger = logging.getLogger(__name__)

EXCEPTION_MAP = {
    langchain_exceptions.LangChainException: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    langchain_exceptions.TracerException: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    langchain_exceptions.OutputParserException: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    SmarterValueError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    SmarterConfigurationError: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    SmarterIlligalInvocationError: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
    ValueError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    TypeError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    NotImplementedError: (HTTPStatus.BAD_REQUEST, "BadRequest"),
    Exception: (HTTPStatus.INTERNAL_SERVER_ERROR, "InternalServerError"),
}


# pylint: disable=too-many-locals,too-many-statements,too-many-arguments
def handler(
    chat: Chat,
    data: dict,
    plugins: List[PluginStatic] = None,
    user: UserType = None,
    default_system_role: str = SmarterLLMDefaults.SYSTEM_ROLE,
    default_temperature: float = SmarterLLMDefaults.TEMPERATURE,
    default_max_tokens: int = SmarterLLMDefaults.MAX_TOKENS,
) -> dict:
    """
    Chat prompt handler. Responsible for processing incoming requests and
    invoking the appropriate OpenAI API endpoint based on the contents of
    the request.

    Args:
        chat: Chat instance
        data: Request data (see below)
        plugins: a List of plugins to potentially show to the LLM
        user: User instance
        llm_vendor: LLMVendor instance: OpenAI, Anthropic, Cohere, Google, Mistral, etc.
        default_model: Default model to use for the chat completion example: "gpt-3.5-turbo"
        default_temperature: Default temperature to use for the chat completion example: 0.5
        default_max_tokens: Default max tokens to use for the chat completion example: 256

    data: {
        'session_key': '6f3bdd1981e0cac2de5fdc7afc2fb4e565826473a124153220e9f6bf49bca67b',
        'messages': [
                {
                    'role': 'system',
                    'content': "You are a helpful assistant."
                },
                {
                    'role': 'assistant',
                    'content': "Welcome to Smarter!. Following are some example prompts: blah blah blah"
                },
                {
                    'role': 'user',
                    'content': 'Hello, World!'
                }
            ]
        }
    """
    request_meta_data: dict = None
    first_iteration = {}
    first_response = {}
    second_iteration = {}
    first_response_dict: Optional[dict] = None
    second_response_dict: Optional[dict] = None
    serialized_tool_calls: Optional[List[Dict]] = None
    messages: List[Dict] = []
    input_text: Optional[str] = None

    weather_tool = weather_tool_factory()
    tools = [weather_tool]
    available_functions = {
        "get_current_weather": get_current_weather,
    }
    try:
        # initializations. we're mainly concerned with ensuring consistent application
        # of default values in cases where chat.chatbot or chat.chatbot.llm_vendor is None,
        # or the specific chatbot attribute is not set.
        llm_vendor = chat.chatbot.llm_vendor or llm_vendors.get_default_llm_vendor()
        model = chat.chatbot.default_model or llm_vendor.default_model
        default_system_role = chat.chatbot.default_system_role or default_system_role

        request_body = get_request_body(data=data)
        messages, input_text = parse_request(request_body)
        messages = ensure_system_role_present(messages=messages, default_system_role=default_system_role)

        temperature = chat.chatbot.default_temperature or default_temperature
        max_tokens = chat.chatbot.default_max_tokens or default_max_tokens
        request_meta_data = request_meta_data_factory(model, temperature, max_tokens, input_text)
        chat_invoked.send(sender=handler, chat=chat, data=data)

        # vendor configuration settings. The model is validated against the vendor's available models
        # as defined in the subclass of LLMVendor. Temperature and max_tokens behave commonly
        # across all vendors.
        llm_vendor.configure(
            model_name=model,
            temperature=temperature,
            max_tokens=max_tokens,
        )

        # does the prompt have anything to do with any of the search terms defined in a plugin?
        # FIX NOTE: need to decide on how to resolve which of many plugin values sets to use for model, temperature, max_tokens
        logger.warning(
            "smarter.apps.chat.providers.langchain.handler(): plugins selector needs to be refactored to use Django model."
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
            valid_items=llm_vendor.all_models,
            item_type="ChatCompletion models",
        )

        # validate_completion_request(request_body, version="v1")
        first_iteration["request"] = {
            "model": model,
            "messages": messages,
            "tools": tools,
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        # LangChain methodology for binding tools to the model.
        # according to the LangChain documentation, there are a few
        # ways to bind tools to the model. We're sticking with the
        # original native OpenAI API method.
        llm_vendor.chat_llm.bind_tools(tools=tools)
        first_response: AIMessage = llm_vendor.chat_llm.invoke(messages=messages)

        first_response_dict = first_response.to_json()
        first_iteration["response"] = first_response_dict
        chat_completion_called.send(
            sender=handler,
            chat=chat,
            iteration=1,
            request=first_iteration["request"],
            response=first_iteration["response"],
        )
        usage_metadata: Optional[UsageMetadata] = first_response.usage_metadata
        create_prompt_completion_charge(
            reference=handler.__name__,
            user_id=user.id,
            model=model,
            completion_tokens=usage_metadata.output_tokens,
            prompt_tokens=usage_metadata.input_tokens,
            total_tokens=usage_metadata.total_tokens,
            fingerprint=first_response.id,
        )
        response_message = first_response.content
        invalid_tool_calls: List[InvalidToolCall] = first_response.invalid_tool_calls
        if invalid_tool_calls:
            chat_completion_invalid_tool_call.send(
                sender=handler, chat=chat, invalid_tool_calls=invalid_tool_calls, request=first_iteration
            )
            raise SmarterIlligalInvocationError("Invalid tool call detected in the response.")

        tool_calls: List[ToolCall] = first_response.tool_calls
        if tool_calls:
            modified_messages = messages.copy()
            # this is intended to force a json serialization exception
            # in the event that we've neglected to properly serialize all
            # responses from openai api.
            serialized_messages: list = json.loads(json.dumps(modified_messages))
            serialized_messages.append(response_message)
            serialized_tool_calls = []

            # Step 3: call the function
            # Note: the JSON response may not always be valid; be sure to handle errors
            modified_messages.append(response_message)  # extend conversation with assistant's reply

            # Step 4: send the info for each function call and function response to the model

            for tool_call in tool_calls:
                serialized_tool_call = {}
                plugin: PluginStatic = None
                function_name: str = tool_call.name
                function_to_call: str = available_functions[function_name]
                function_args: Dict[str, Any] = tool_call.args
                function_id: Optional[str] = tool_call.id
                serialized_tool_call["function_name"] = function_name
                serialized_tool_call["function_args"] = function_args

                function_response = None
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
                    plugin = PluginStatic(plugin_id=plugin_id)
                    plugin.params = function_args
                    function_response = plugin.function_calling_plugin(inquiry_type=function_args.get("inquiry_type"))
                    serialized_tool_call["smarter_plugin"] = PluginMetaSerializer(plugin.plugin_meta).data
                tool_call_message = {
                    "tool_call_id": function_id,
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
            second_response: AIMessage = llm_vendor.chat_llm.invoke(messages=modified_messages)
            second_response_dict = second_response.to_json()
            second_iteration["response"] = second_response_dict
            second_iteration["request"]["messages"] = serialized_messages
            chat_completion_tool_call_created.send(
                sender=handler,
                chat=chat,
                tool_calls=serialized_tool_calls,
                request=second_iteration["request"],
                response=second_iteration["response"],
            )
            usage_metadata: Optional[UsageMetadata] = second_response.usage_metadata
            create_plugin_charge(
                reference=handler.__name__,
                user_id=user.id,
                model=model,
                completion_tokens=usage_metadata.output_tokens,
                prompt_tokens=usage_metadata.input_tokens,
                total_tokens=usage_metadata.total_tokens,
                fingerprint=first_response.id,
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
    response["metadata"] = {"tool_calls": serialized_tool_calls, **request_meta_data}
    chat_response_success.send(sender=handler, chat=chat, request=first_iteration.get("request"), response=response)
    return http_response_factory(status_code=HTTPStatus.OK, body=response)
