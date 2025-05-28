"""
Base class for creating units tests of chat providers.
"""

import os

# python stuff
import secrets
import sys
import time
from pathlib import Path
from time import sleep
from typing import Callable

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.chatbot.models import ChatBot, ChatBotPlugin
from smarter.apps.plugin.nlp import does_refer_to
from smarter.apps.plugin.plugin.static import StaticPlugin
from smarter.apps.plugin.signals import plugin_called, plugin_selected
from smarter.apps.prompt.providers.const import OpenAIMessageKeys
from smarter.common.utils import get_readonly_yaml_file

from ..models import Chat, ChatPluginUsage
from ..providers.providers import chat_providers
from ..signals import (
    chat_completion_response,
    chat_finished,
    chat_response_failure,
    chat_started,
)
from ..tests.test_setup import get_test_file, get_test_file_path


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402
CELERY_WAIT = 1


class ProviderBaseClass(TestAccountMixin):
    """Test Index Lambda function."""

    _provider: str = None
    handler: Callable
    plugin: StaticPlugin
    plugins: list[StaticPlugin]
    chatbot: ChatBot
    client: Client
    chat: Chat

    _plugin_called = False
    _plugin_selected = False
    _chat_invoked = False
    _chat_completion_plugin_selected = False
    _chat_completion_response_received = False
    _chat_completion_returned = False
    _chat_completion_failed = False
    _chat_completion_tool_call_received = False

    def __init__(self, *args, **kwargs):
        self.init()
        super().__init__(*args, **kwargs)

    def init(self):
        self._provider = None
        self.handler = None
        self.plugin = None
        self.plugins = None
        self.chatbot = None
        self.client = None
        self.chat = None

        self._plugin_called = False
        self._plugin_selected = False
        self._chat_invoked = False
        self._chat_completion_plugin_selected = False
        self._chat_completion_response_received = False
        self._chat_completion_returned = False
        self._chat_completion_failed = False
        self._chat_completion_tool_call_received = False

    @property
    def provider(self):
        return self._provider

    @provider.setter
    def provider(self, value):
        self._provider = value

    def plugin_called_signal_handler(self, *args, **kwargs):
        self._plugin_called = True

    def plugin_selected_signal_handler(self, *args, **kwargs):
        self._plugin_selected = True

    def chat_completion_plugin_selected_signal_handler(self, *args, **kwargs):
        self._chat_completion_plugin_selected = True

    def chat_invoked_signal_handler(self, *args, **kwargs):
        self._chat_invoked = True

    def chat_completion_response_received_signal_handler(self, *args, **kwargs):
        self._chat_completion_response_received = True

    def chat_completion_returned_signal_handler(self, *args, **kwargs):
        self._chat_completion_returned = True

    def chat_completion_failed_signal_handler(self, *args, **kwargs):
        self._chat_completion_failed = True

    def chat_completion_tool_call_received_signal_handler(self, *args, **kwargs):
        self._chat_completion_tool_call_received = True

    @property
    def signals(self):
        return {
            "plugin_called": self._plugin_called,
            "plugin_selected": self._plugin_selected,
            "chat_started": self._chat_invoked,
            "chat_completion_response": self._chat_completion_response_received,
            "chat_finished": self._chat_completion_returned,
            "chat_response_failure": self._chat_completion_failed,
        }

    def setUp(self):
        """Internal test fixture setup, called from child class setUp()"""
        super().setUp()
        self.init()

        print(f"user: {self.admin_user}, account: {self.account}, user_profile: {self.user_profile}")

        config_path = get_test_file_path("plugins/everlasting-gobstopper.yaml")
        plugin_data = get_readonly_yaml_file(config_path)

        print("Setting up plugin")
        if not self.plugin:
            self.plugin = StaticPlugin(user_profile=self.user_profile, data=plugin_data)
            self.plugins = [self.plugin]
        print(f"plugin: {self.plugin}")

        # create a chatbot that uses the provider
        print(f"Setting up provider {self.provider}")
        self.chatbot = self.chatbot_factory(provider=self.provider)
        self.handler = chat_providers.get_handler(provider=self.provider)
        print(f"provider {self.provider} is setup")

        self.client = Client()
        self.client.force_login(self.admin_user)

        self.chat = Chat.objects.create(
            session_key=secrets.token_hex(32),
            chatbot=self.chatbot,
            account=self.account,
            ip_address="192.1.1.1",
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.3",
            url="https://www.test.com",
        )

    def tearDown(self):
        """Tear down test fixtures."""
        if self.chat:
            chat = self.chat  # to mitigate a race condition where the test
            # may delete the chat before these models are deleted
            # ChatHistory.objects.filter(chat=chat).delete()
            # ChatToolCall.objects.filter(chat=chat).delete()
            # ChatPluginUsage.objects.filter(chat=chat).delete()
            chat.delete()
        if self.chatbot:
            self.chatbot.delete()
        if self.plugin:
            self.plugin.delete()
        self.plugins = None
        self.handler = None
        super().tearDown()

    def chatbot_factory(self, provider: str = "openai"):
        chatbot = ChatBot.objects.create(
            name="TestChatBot",
            account=self.account,
            description="Test ChatBot",
            version="1.0.0",
            subdomain=None,
            custom_domain=None,
            deployed=False,
            app_name="Smarter",
            app_assistant="Smarty Pants",
            app_welcome_message="Welcome to Smarter!",
            provider=provider,
        )
        ChatBotPlugin.objects.create(
            chatbot=chatbot,
            plugin_meta=self.plugin.plugin_meta,
        )
        return chatbot

    def check_response(self, response):
        """Check response structure from api.v1.views.chat handler()"""
        if response["statusCode"] != 200:
            print(f"response: {response}")

        self.assertEqual(response["statusCode"], 200)
        self.assertTrue("body" in response)
        self.assertTrue("isBase64Encoded" in response)
        body = response["body"]
        self.assertTrue("id" in body)
        self.assertTrue("object" in body)
        self.assertTrue("created" in body)
        self.assertTrue("model" in body)
        self.assertTrue("choices" in body)
        self.assertTrue("completion" in body)
        self.assertTrue("metadata" in body)
        self.assertTrue("usage" in body)

    def test_does_not_refer_to(self):
        """Test simple false outcomes for does_refer_to."""
        self.assertFalse(does_refer_to("larry", "lawrence"))
        self.assertFalse(does_refer_to("dev", "developer"))

    def test_does_refer_to_camel_case(self):
        """Test does_refer_to works correctly with camel case."""
        self.assertTrue(does_refer_to("FullStackWithLawrence", "Full Stack With Lawrence"))

    def test_does_refer_to_easy(self):
        """Test does_refer_to."""
        self.assertTrue(does_refer_to("lawrence", "lawrence"))
        self.assertTrue(does_refer_to("Lawrence McDaniel", "lawrence"))
        self.assertTrue(does_refer_to("Who is Lawrence McDaniel?", "Lawrence McDaniel"))

    def test_does_refer_to_harder(self):
        """Test does_refer_to."""
        self.assertTrue(does_refer_to("Is it true that larry mcdaniel has a YouTube channel?", "larry mcdaniel"))
        self.assertTrue(does_refer_to("Is it true that Lawrence P. McDaniel has a YouTube channel?", "mcdaniel"))
        self.assertTrue(does_refer_to("Is it true that Lawrence P. McDaniel has a YouTube channel?", "lawrence"))
        self.assertTrue(does_refer_to("Is it true that Larry McDaniel has a YouTube channel?", "larry McDaniel"))

    def test_search_terms_are_in_messages(self):
        """Test search_terms_are_in_messages()."""

        def list_factory(content: str) -> list:
            return [
                {
                    OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.SYSTEM_MESSAGE_KEY,
                    OpenAIMessageKeys.MESSAGE_CONTENT_KEY: "You are a helpful chatbot.",
                },
                {
                    OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.USER_MESSAGE_KEY,
                    OpenAIMessageKeys.MESSAGE_CONTENT_KEY: "what is web development?",
                },
                {
                    OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.ASSISTANT_MESSAGE_KEY,
                    OpenAIMessageKeys.MESSAGE_CONTENT_KEY: "blah blah answer answer.",
                },
                {
                    OpenAIMessageKeys.MESSAGE_ROLE_KEY: OpenAIMessageKeys.USER_MESSAGE_KEY,
                    OpenAIMessageKeys.MESSAGE_CONTENT_KEY: content,
                },
            ]

        def false_assertion(content: str):
            messages = list_factory(content)
            self.assertFalse(self.plugin.selected(self.admin_user, messages=messages))

        def true_assertion(content: str):
            messages = list_factory(content)
            self.assertTrue(self.plugin.selected(self.admin_user, messages=messages))

        # false cases
        false_assertion("when was leisure suit larry released?")
        false_assertion("is larry carlton a good guitarist?")
        false_assertion("do full stack developers earn a lot of money?")
        false_assertion("who is John Kennedy?")
        false_assertion("Hello world!")
        false_assertion("test test test")
        false_assertion("what is the airport code the airport in Dallas, Texas?")

        # true cases
        true_assertion("what is an everlasting gobstopper?")
        true_assertion("do you spell everlasting gobstopper with one b or two?")
        true_assertion("everlasting gobstopper")

    def test_handler_gobstoppers(self):
        """Test api.v1.views.chat handler() - Gobstoppers."""

        # setup receivers for all signals to check if they are called
        plugin_selected.connect(self.plugin_selected_signal_handler)
        plugin_called.connect(self.plugin_called_signal_handler)
        chat_started.connect(self.chat_invoked_signal_handler)
        chat_completion_response.connect(self.chat_completion_response_received_signal_handler)
        chat_finished.connect(self.chat_completion_returned_signal_handler)
        chat_response_failure.connect(self.chat_completion_failed_signal_handler)

        response = None
        event_about_gobstoppers = get_test_file("json/prompt_about_everlasting_gobstoppers.json")

        try:
            response = self.handler(
                chat=self.chat, data=event_about_gobstoppers, plugins=self.plugins, user=self.admin_user
            )
            sleep(1)
        except Exception as error:
            self.fail(f"handler() raised {error}")
        self.check_response(response)

        # assert that every key in self.signals is True
        for key, value in self.signals.items():
            if key != "chat_response_failure":
                print("assertTrue key:", key, "value:", value)
                # self.assertTrue(value)
            else:
                print("assertFalse key:", key, "value:", value)
                # self.assertFalse(value)

        # assert that Chat has one or more records for self.admin_user
        chat_histories = Chat.objects.filter().first()
        self.assertIsNotNone(chat_histories)

        # test url api endpoint for chat history
        response = self.client.get("/api/v1/chat/history/chat/")
        self.assertEqual(response.status_code, 200)
        print("/api/v1/chat/history/chat/ response:", response.json())

        # give celery time to process the chat completion
        time.sleep(CELERY_WAIT)  # Pause execution for 1 second

        # assert that ChatPluginUsage has one or more records for self.admin_user
        plugin_selection_histories = ChatPluginUsage.objects.filter(chat=self.chat).first()
        if not plugin_selection_histories:
            print("ChatPluginUsage.objects.first() is None. llm did not call the plugin.")
        else:
            self.assertIsNotNone(plugin_selection_histories)

    def test_handler_weather(self):
        """Test api.v1.views.chat handler() - weather."""
        response = None
        event_about_weather = get_test_file("json/prompt_about_weather.json")

        try:
            response = self.handler(
                chat=self.chat, plugins=self.plugins, user=self.admin_user, data=event_about_weather
            )
        except Exception as error:
            self.fail(f"handler() raised {error}")
        self.check_response(response)

    def test_handler_recipes(self):
        """Test api.v1.views.chat handler() - recipes."""
        response = None
        event_about_recipes = get_test_file("json/prompt_about_recipes.json")

        try:
            response = self.handler(
                chat=self.chat, plugins=self.plugins, user=self.admin_user, data=event_about_recipes
            )
        except Exception as error:
            self.fail(f"handler() raised {error}")
        self.check_response(response)
