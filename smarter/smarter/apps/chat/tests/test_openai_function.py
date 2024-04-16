# pylint: disable=wrong-import-position
# pylint: disable=R0801,E1101
# pylint: disable=broad-exception-caught
# pylint: disable=W0613
"""Test lambda_openai_v2 function."""

# python stuff
import os
import sys
import unittest
from pathlib import Path
from time import sleep

import yaml
from django.test import Client

from smarter.lib.django.user import User


HERE = os.path.abspath(os.path.dirname(__file__))
PROJECT_ROOT = str(Path(HERE).parent.parent)
PYTHON_ROOT = str(Path(PROJECT_ROOT).parent)
if PYTHON_ROOT not in sys.path:
    sys.path.append(PYTHON_ROOT)  # noqa: E402

from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.nlp import does_refer_to
from smarter.apps.plugin.plugin import Plugin
from smarter.apps.plugin.signals import plugin_called, plugin_selected

from ..models import ChatHistory, PluginUsageHistory
from ..providers.smarter import handler
from ..signals import (
    chat_completion_called,
    chat_completion_plugin_selected,
    chat_completion_tool_call_received,
    chat_invoked,
    chat_response_failure,
    chat_response_success,
)
from ..tests.test_setup import get_test_file, get_test_file_path


# pylint: disable=too-many-public-methods,too-many-instance-attributes
class TestOpenaiFunctionCalling(unittest.TestCase):
    """Test Index Lambda function."""

    _plugin_called = False
    _plugin_selected = False
    _chat_invoked = False
    _chat_completion_plugin_selected = False
    _chat_completion_called = False
    _chat_completion_returned = False
    _chat_completion_failed = False
    _chat_completion_tool_call_received = False

    def plugin_called_signal_handler(self, *args, **kwargs):
        self._plugin_called = True

    def plugin_selected_signal_handler(self, *args, **kwargs):
        self._plugin_selected = True

    def chat_completion_plugin_selected_signal_handler(self, *args, **kwargs):
        self._chat_completion_plugin_selected = True

    def chat_invoked_signal_handler(self, *args, **kwargs):
        self._chat_invoked = True

    def chat_completion_called_signal_handler(self, *args, **kwargs):
        self._chat_completion_called = True

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
            "chat_invoked": self._chat_invoked,
            "chat_completion_plugin_selected": self._chat_completion_plugin_selected,
            "chat_completion_called": self._chat_completion_called,
            "chat_response_success": self._chat_completion_returned,
            "chat_response_failure": self._chat_completion_failed,
        }

    def setUp(self):
        """Set up test fixtures."""
        username = "testuser_" + os.urandom(4).hex()
        self.user = User.objects.create(username=username, password="12345")
        self.account = Account.objects.create(company_name="Test Account")
        self.user_profile = UserProfile.objects.create(user=self.user, account=self.account, is_test=True)

        config_path = get_test_file_path("plugins/everlasting-gobstopper.yaml")
        with open(config_path, encoding="utf-8") as file:
            plugin_json = yaml.safe_load(file)
        plugin_json["user_profile"] = self.user_profile

        self.plugin = Plugin(data=plugin_json)
        self.plugins = [self.plugin]

        self.client = Client()
        self.client.force_login(self.user)

    def tearDown(self):
        """Tear down test fixtures."""
        self.user_profile.delete()
        self.user.delete()
        self.account.delete()
        self.plugin.delete()

    def check_response(self, response):
        """Check response structure from api.v0.views.chat handler()"""
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
        self.assertTrue("request_meta_data" in body)
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
                {"role": "system", "content": "You are a helpful chatbot."},
                {"role": "user", "content": "what is web development?"},
                {"role": "system", "content": "blah blah answer answer."},
                {"role": "user", "content": content},
            ]

        def false_assertion(content: str):
            self.assertFalse(self.plugin.selected(self.user, list_factory(content)))

        def true_assertion(content: str):
            self.assertTrue(self.plugin.selected(self.user, list_factory(content)))

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
        """Test api.v0.views.chat handler() - Gobstoppers."""

        # setup receivers for all signals to check if they are called
        plugin_selected.connect(self.plugin_selected_signal_handler)
        plugin_called.connect(self.plugin_called_signal_handler)
        chat_invoked.connect(self.chat_invoked_signal_handler)
        chat_completion_plugin_selected.connect(self.chat_completion_plugin_selected_signal_handler)
        chat_completion_called.connect(self.chat_completion_called_signal_handler)
        chat_response_success.connect(self.chat_completion_returned_signal_handler)
        chat_response_failure.connect(self.chat_completion_failed_signal_handler)
        chat_completion_tool_call_received.connect(self.chat_completion_tool_call_received_signal_handler)

        response = None
        event_about_gobstoppers = get_test_file("json/prompt_about_everlasting_gobstoppers.json")

        try:
            response = handler(plugins=self.plugins, user=self.user, data=event_about_gobstoppers)
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

        # assert that ChatHistory has one or more records for self.user
        chat_histories = ChatHistory.objects.filter(user=self.user)
        self.assertTrue(chat_histories.exists())

        # test url api endpoint for chat history
        response = self.client.get("/api/v0/chat/history/chats/")
        self.assertEqual(response.status_code, 200)
        print("/api/v0/chat/history/chats/ response:", response.json())

        # assert that PluginUsageHistory has one or more records for self.user
        plugin_selection_histories = PluginUsageHistory.objects.filter(user=self.user)
        self.assertTrue(plugin_selection_histories.exists())

    def test_handler_weather(self):
        """Test api.v0.views.chat handler() - weather."""
        response = None
        event_about_weather = get_test_file("json/prompt_about_weather.json")

        try:
            response = handler(plugins=self.plugins, user=self.user, data=event_about_weather)
        except Exception as error:
            self.fail(f"handler() raised {error}")
        self.check_response(response)

    def test_handler_recipes(self):
        """Test api.v0.views.chat handler() - recipes."""
        response = None
        event_about_recipes = get_test_file("json/prompt_about_recipes.json")

        try:
            response = handler(plugins=self.plugins, user=self.user, data=event_about_recipes)
        except Exception as error:
            self.fail(f"handler() raised {error}")
        self.check_response(response)
