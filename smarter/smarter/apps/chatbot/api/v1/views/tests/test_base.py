"""Test ChatBotApiBaseViewSet"""

import os
import unittest
from io import BytesIO

from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest
from django.test import Client

from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker
from smarter.apps.plugin.utils import add_example_plugins
from smarter.lib.unittest.utils import get_readonly_yaml_file

from ..base import ChatBotApiBaseViewSet


HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=too-many-instance-attributes
class TestChatBotApiBaseViewSet(unittest.TestCase):
    """Test SAM Chatbot Broker"""

    # pylint: disable=W0212
    @classmethod
    def create_generic_request(cls, url: str) -> HttpRequest:
        request = HttpRequest()
        request.method = "POST"
        request.META["SERVER_NAME"], request.META["SERVER_PORT"] = url.split("/")[2].split(":")
        request._read_started = False
        request._stream = WSGIRequest({"REQUEST_METHOD": "POST", "wsgi.input": BytesIO()})
        return request

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        cls.user, cls.account, cls.user_profile = admin_user_factory()

        config_path = os.path.join(HERE, "data/chatbot.yaml")
        cls.manifest = get_readonly_yaml_file(config_path)
        cls.broker = SAMChatbotBroker(request=None, account=cls.account, manifest=cls.manifest)
        cls.request = cls.create_generic_request(url=cls.broker.chatbot.url_chatbot)

        cls.request.user = cls.user
        cls.client = Client()
        cls.client.force_login(cls.user)
        cls.kwargs = {}
        add_example_plugins(user_profile=cls.user_profile)

        cls.broker.apply(request=cls.request, kwargs=cls.kwargs)

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        admin_user_teardown(cls.user, cls.account, cls.user_profile)
        cls.broker.delete(request=cls.request, kwargs=cls.kwargs)

    def test_base_class_properties(self):
        base_class = ChatBotApiBaseViewSet()
        base_class.request = self.request

        # invoke dispatch method in order to set our class properties
        base_class.dispatch(self.request, name=self.broker.chatbot.name)

        self.assertEqual(base_class.chatbot_helper.account_number, self.account.account_number)
        self.assertEqual(base_class.chatbot_helper.user, self.user)
        self.assertEqual(base_class.chatbot_helper.user_profile, self.user_profile)
        self.assertEqual(base_class.chatbot_helper.chatbot, self.broker.chatbot)
        self.assertTrue(base_class.is_web_platform)
