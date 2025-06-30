"""Test ChatBotApiBaseViewSet"""

import json
import logging
import os

from django.core.handlers.wsgi import WSGIRequest
from django.test import Client, RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker
from smarter.apps.plugin.utils import add_example_plugins
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from ..base import ChatBotApiBaseViewSet


HERE = os.path.abspath(os.path.dirname(__file__))


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CHATBOT_LOGGING) and level <= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


# pylint: disable=too-many-instance-attributes
class TestChatBotApiBaseViewSet(TestAccountMixin):
    """Test SAM Chatbot Broker"""

    # pylint: disable=W0212
    @classmethod
    def create_generic_request(cls, url: str) -> WSGIRequest:
        factory = RequestFactory()
        json_data = {
            "session_key": "6f3bdd1981e0cac2de5fdc7afc2fb4e565826473a124153220e9f6bf49bca67b",
            "messages": [
                {"role": "system", "content": "You are a helpful assistant."},
                {
                    "role": "assistant",
                    "content": "Welcome to Smarter!. Following are some example prompts: blah blah blah",
                },
                {"role": "smarter", "content": 'Tool call: function_calling_plugin_0002({"inquiry_type":"about"})'},
                {"role": "user", "content": "Hello, World!"},
            ],
        }
        json_data = json.dumps(json_data).encode("utf-8")
        request: WSGIRequest = factory.post(path=url, data=json_data, content_type="application/json")
        return request

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        config_path = os.path.join(HERE, "data/chatbot.yaml")
        cls.manifest = get_readonly_yaml_file(config_path)
        cls.broker = SAMChatbotBroker(request=None, account=cls.account, manifest=cls.manifest)
        cls.request: WSGIRequest = cls.create_generic_request(url=cls.broker.chatbot.url_chatbot)

        cls.request.user = cls.admin_user
        cls.client = Client()
        cls.client.force_login(cls.admin_user)
        cls.kwargs = {}

        # Add example plugins to the user profile
        add_example_plugins(user_profile=cls.user_profile)

        cls.broker.apply(request=cls.request, kwargs=cls.kwargs)

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        try:
            cls.broker.delete(request=cls.request, kwargs=cls.kwargs)
        # pylint: disable=W0718
        except Exception:
            pass
        finally:
            super().tearDownClass()

    def test_base_class_properties(self):
        base_class = ChatBotApiBaseViewSet()

        # invoke dispatch method in order to set our class properties
        base_class.dispatch(self.request, name=self.broker.chatbot.name)

        logger.info(f"test_base_class_properties() request={self.request} name={self.broker.chatbot.name}")
        self.assertEqual(base_class.chatbot_helper.account_number, self.account.account_number)
        self.assertEqual(base_class.chatbot_helper.user, self.admin_user)
        self.assertEqual(base_class.chatbot_helper.user_profile, self.user_profile)
        self.assertEqual(base_class.chatbot_helper.chatbot, self.broker.chatbot)
