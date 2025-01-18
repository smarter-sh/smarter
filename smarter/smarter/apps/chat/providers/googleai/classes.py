# pylint: disable=R0801
"""
GoogleAI chat provider. Implements the following three things:
Compatibility with GoogleAI chat provider: https://ai.google.dev/gemini-api/docs/openai

1. EXCEPTION_MAP: A dictionary that maps exceptions to HTTP status codes and error types.
2. GoogleAIHandlerInput: Input protocol for GoogleAI chat provider handler.
3. GoogleAIChatProvider: GoogleAI chat provider.
"""
import json
import logging
from http import HTTPStatus

# 3rd party stuff
import openai

# smarter chat provider stuff
from smarter.apps.chat.providers.classes import ChatProviderBase, HandlerInputBase
from smarter.apps.chat.providers.openai.classes import EXCEPTION_MAP
from smarter.apps.chat.providers.openai.const import OpenAIMessageKeys
from smarter.apps.chat.providers.utils import (
    clean_messages,
    ensure_system_role_present,
    exception_response_factory,
    get_request_body,
    http_response_factory,
    parse_request,
    request_meta_data_factory,
)
from smarter.apps.chat.providers.validators import validate_item
from smarter.apps.chat.signals import (
    chat_completion_request,
    chat_completion_response,
    chat_completion_tool_called,
    chat_invocation_finished,
    chat_invocation_start,
    chat_response_failure,
)
from smarter.apps.plugin.plugin.static import PluginStatic
from smarter.apps.plugin.serializers import PluginMetaSerializer
from smarter.common.classes import Singleton
from smarter.common.conf import settings as smarter_settings

from .const import BASE_URL, DEFAULT_MODEL, PROVIDER_NAME, VALID_CHAT_COMPLETION_MODELS


logger = logging.getLogger(__name__)


# 2.) GoogleAIHandlerInput: Input protocol for GoogleAI chat provider handler.
class GoogleAIHandlerInput(HandlerInputBase):
    """
    Input protocol for GoogleAI chat provider handler.
    """

    default_model: str = DEFAULT_MODEL
    default_system_role: str = smarter_settings.llm_default_system_role
    default_temperature: float = smarter_settings.llm_default_temperature
    default_max_tokens: int = smarter_settings.llm_default_max_tokens


# 3.) GoogleAIChatProvider: GoogleAI chat provider.
class GoogleAIChatProvider(ChatProviderBase, metaclass=Singleton):
    """
    GoogleAI chat provider.
    """

    def __init__(self):
        super().__init__(
            name=PROVIDER_NAME,
            default_model=DEFAULT_MODEL,
            exception_map=EXCEPTION_MAP,
            base_url=BASE_URL,
            api_key=smarter_settings.gemini_api_key.get_secret_value(),
        )
        self._validate_default_model(model=DEFAULT_MODEL)

    @property
    def valid_models(self) -> list[str]:
        return VALID_CHAT_COMPLETION_MODELS

    # pylint: disable=too-many-locals,too-many-statements,too-many-arguments
    def handler(
        self,
        handler_inputs: GoogleAIHandlerInput,
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
            default_model: Default model to use for the chat completion example: "gpt-4-turbo"
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
        openai.api_key = self.api_key
        openai.base_url = self.base_url

        # populate the handler inputs from the Pydantic input protocol
        chat = handler_inputs.chat
        data = handler_inputs.data
        plugins = handler_inputs.plugins
        user = handler_inputs.user
        default_model = handler_inputs.default_model
        default_system_role = handler_inputs.default_system_role
        default_temperature = handler_inputs.default_temperature
        default_max_tokens = handler_inputs.default_max_tokens

        # validations
        if not chat:
            raise ValueError(f"{self.__class__.__name__}: chat object is required")
        if not data:
            raise ValueError(f"{self.__class__.__name__}: data object is required")
        if not user:
            raise ValueError(f"{self.__class__.__name__}: user object is required")
        if not default_model:
            raise ValueError(f"{self.__class__.__name__}: default_model is required")
        if not default_system_role:
            raise ValueError(f"{self.__class__.__name__}: default_system_role is required")
        if not default_temperature:
            raise ValueError(f"{self.__class__.__name__}: default_temperature is required")
        if not default_max_tokens:
            raise ValueError(f"{self.__class__.__name__}: default_max_tokens is required")

        # initialize our local variables
        request_meta_data: dict = None
        first_iteration = {}
        first_response = {}
        second_response = {}
        second_iteration = {}
        first_response_dict: dict = None
        second_response_dict: dict = None
        serialized_tool_calls: list[dict] = None
        messages: list[dict] = None
        input_text: str = None

        try:
            model = chat.chatbot.default_model or default_model
            default_system_role = chat.chatbot.default_system_role or default_system_role

            request_body = get_request_body(data=data)
            messages, input_text = parse_request(request_body)
            messages = ensure_system_role_present(messages=messages, default_system_role=default_system_role)
            messages = clean_messages(messages=messages)

            temperature = chat.chatbot.default_temperature or default_temperature
            max_tokens = chat.chatbot.default_max_tokens or default_max_tokens
            request_meta_data = request_meta_data_factory(model, temperature, max_tokens, input_text)
            chat_invocation_start.send(sender=GoogleAIChatProvider.handler, chat=chat, data=data)

            # does the prompt have anything to do with any of the search terms defined in a plugin?
            # FIX NOTE: need to decide on how to resolve which of many plugin values sets to use for model, temperature, max_tokens
            logger.warning(
                "smarter.apps.chat.providers.openai.handler(): plugins selector needs to be refactored to use Django model."
            )
            for plugin in plugins:
                if plugin.selected(user=user, input_text=input_text):
                    model = plugin.plugin_prompt.model
                    temperature = plugin.plugin_prompt.temperature
                    max_tokens = plugin.plugin_prompt.max_tokens
                    messages = plugin.customize_prompt(messages)
                    custom_tool = plugin.custom_tool
                    self.tools.append(custom_tool)
                    self.available_functions[plugin.function_calling_identifier] = plugin.function_calling_plugin
                    self.append_message_plugin_selected(plugin=plugin.plugin_meta.name)

            # https://platform.openai.com/docs/guides/gpt/chat-completions-api
            validate_item(
                item=model,
                valid_items=VALID_CHAT_COMPLETION_MODELS,
                item_type="ChatCompletion models",
            )

            # validate_completion_request(request_body, version="v1")
            first_iteration["request"] = {
                "model": model,
                "messages": messages,
                "tools": self.tools,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }

            self.handle_first_prompt(
                model=model,
                tools=self.tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
            )

            chat_completion_request.send(
                sender=GoogleAIChatProvider.handler,
                chat=chat,
                iteration=1,
                request=first_iteration["request"],
            )

            first_response = openai.chat.completions.create(
                model=model,
                messages=messages,
                tools=self.tools,
                tool_choice="auto",
                temperature=temperature,
                max_tokens=max_tokens,
            )

            first_response_dict = json.loads(first_response.model_dump_json())
            first_iteration["response"] = first_response_dict
            chat_completion_response.send(
                sender=GoogleAIChatProvider.handler,
                chat=chat,
                iteration=1,
                request=first_iteration["request"],
                response=first_iteration["response"],
            )
            self.handle_prompt_completion_response(
                user_id=user.id,
                model=model,
                completion_tokens=first_response.usage.completion_tokens,
                prompt_tokens=first_response.usage.prompt_tokens,
                total_tokens=first_response.usage.total_tokens,
                system_fingerprint=first_response.system_fingerprint,
                response_message_role=first_response.choices[0].message.role,
                response_message_content=first_response.choices[0].message.content,
            )
            response_message = first_response.choices[0].message
            tool_calls = response_message.tool_calls
            if tool_calls:
                modified_messages = messages.copy()
                modified_messages = clean_messages(messages=modified_messages)
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
                    plugin: PluginStatic = None
                    function_name = tool_call.function.name
                    function_to_call = self.available_functions[function_name]
                    function_args = json.loads(tool_call.function.arguments)
                    serialized_tool_call["function_name"] = function_name
                    serialized_tool_call["function_args"] = function_args
                    self.append_message_tool_called(function_name=function_name, function_args=function_args)

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
                        function_response = plugin.function_calling_plugin(
                            inquiry_type=function_args.get("inquiry_type")
                        )
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
                chat_completion_response.send(
                    sender=GoogleAIChatProvider.handler, chat=chat, iteration=2, request=second_iteration["request"]
                )
                second_response = openai.chat.completions.create(
                    model=model,
                    messages=modified_messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )  # get a new response from the model where it can see the function response
                second_response_dict = json.loads(second_response.model_dump_json())
                second_iteration["response"] = second_response_dict
                second_iteration["request"]["messages"] = serialized_messages
                self.handle_prompt_completion_response(
                    user_id=user.id,
                    model=model,
                    completion_tokens=second_response.usage.completion_tokens,
                    prompt_tokens=second_response.usage.prompt_tokens,
                    total_tokens=second_response.usage.total_tokens,
                    system_fingerprint=second_response.system_fingerprint,
                    response_message_role=second_response.choices[0].message.role,
                    response_message_content=second_response.choices[0].message.content,
                )
                chat_completion_tool_called.send(
                    sender=GoogleAIChatProvider.handler,
                    chat=chat,
                    tool_calls=serialized_tool_calls,
                    request=second_iteration["request"],
                    response=second_iteration["response"],
                )
                self.handle_prompt_completion_plugin(
                    user_id=user.id,
                    model=model,
                    completion_tokens=second_response.usage.completion_tokens,
                    prompt_tokens=second_response.usage.prompt_tokens,
                    total_tokens=second_response.usage.total_tokens,
                    system_fingerprint=second_response.system_fingerprint,
                )

        # handle anything that went wrong
        # pylint: disable=broad-exception-caught
        except Exception as e:
            chat_response_failure.send(
                sender=GoogleAIChatProvider.handler,
                chat=chat,
                request_meta_data=request_meta_data,
                exception=e,
                first_response=first_response_dict,
                second_response=second_response_dict,
            )
            status_code, _message = self.exception_map.get(
                type(e), (HTTPStatus.INTERNAL_SERVER_ERROR, "Internal server error")
            )
            return http_response_factory(
                status_code=status_code,
                body=exception_response_factory(exception=e, request_meta_data=request_meta_data),
            )

        # success!! return the response
        response = second_iteration.get("response") or first_iteration.get("response")
        response["metadata"] = {"tool_calls": serialized_tool_calls, **request_meta_data}
        response[OpenAIMessageKeys.SMARTER_MESSAGE_KEY] = {
            "first_iteration": json.loads(json.dumps(first_iteration)),
            "second_iteration": json.loads(json.dumps(second_iteration)),
            "tools": [tool["function"]["name"] for tool in self.tools],
            "plugins": [plugin.plugin_meta.name for plugin in plugins],
            "messages": self.messages,
        }
        chat_invocation_finished.send(
            sender=GoogleAIChatProvider.handler, chat=chat, request=first_iteration.get("request"), response=response
        )
        return http_response_factory(status_code=HTTPStatus.OK, body=response)


# create an instance of the GoogleAI chat provider singleton
googleai_chat_provider = GoogleAIChatProvider()
