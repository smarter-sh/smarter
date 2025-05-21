"""Test SAM Chatbot Broker"""

import json
import os
from http import HTTPStatus
from logging import getLogger

import requests
import yaml
from django.http import JsonResponse
from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker
from smarter.apps.chatbot.manifest.models.chatbot.model import SAMChatbot
from smarter.apps.plugin.utils import add_example_plugins
from smarter.common.utils import (
    dict_is_contained_in,
    dict_is_subset,
    get_readonly_yaml_file,
)
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.loader import SAMLoader


HERE = os.path.abspath(os.path.dirname(__file__))
logger = getLogger(__name__)


# pylint: disable=too-many-instance-attributes
class TestSAMChatbotBroker(TestAccountMixin):
    """Test SAM Chatbot Broker"""

    @classmethod
    def create_generic_request(cls):
        url = "http://example.com"
        headers = {"Content-Type": "application/json"}
        data = {}

        request = requests.Request("GET", url, headers=headers, data=data)
        prepared_request = request.prepare()

        return prepared_request

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        cls.request = cls.create_generic_request()

        config_path = os.path.join(HERE, "data/chatbot.yaml")
        cls.manifest = get_readonly_yaml_file(config_path)
        cls.broker = SAMChatbotBroker(request=cls.request, account=cls.account, manifest=cls.manifest)
        cls.client = Client()
        cls.kwargs = {}
        add_example_plugins(user_profile=cls.user_profile)

    def test_chatbot_broker_apply(self):
        """Test that the Broker can apply the manifest."""
        retval = self.broker.apply(request=self.request, kwargs=self.kwargs)
        content = json.loads(retval.content.decode())
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], f"Chatbot {self.broker.chatbot.name} applied successfully")

    def test_chatbot_broker_describe(self):
        """
        Test that the Broker can generate and return a valid manifest.
        - create a resource from a manifest
        - describe the resource
        - convert the description from json to yaml
        - load the yaml description into a SAMLoader object
        - create a pydantic model from the loader
        - dump the pydantic model to a dictionary
        """

        retval = self.broker.apply(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        # generate the manifest
        retval = self.broker.describe(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        # transform the json content to a yaml manifest
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        content = content["data"]  # the manifest is loaded into the 'data' key
        content.pop("status")  # status is read-only
        content["spec"]["config"].pop("dnsVerificationStatus")  # dnsVerificationStatus is read-only
        manifest = yaml.dump(content)

        # load the yaml manifest into a SAMLoader object
        loader = SAMLoader(manifest=manifest)

        # create a pydantic model from the loader
        pydantic_model = SAMChatbot(**loader.pydantic_model_dump())

        # dump the pydantic model to a dictionary
        round_trip_dict = json.loads(pydantic_model.model_dump_json())

        # assert that everything in content is in round_trip_dict
        # self.assertTrue(dict_is_subset(content, round_trip_dict), f"content is not contained in round_trip_dict.\n\ncontent: {content}\n\nround_trip_dict:{round_trip_dict}")
        self.assertEqual(content["apiVersion"], round_trip_dict["apiVersion"])
        self.assertEqual(content["kind"], round_trip_dict["kind"])
        self.assertEqual(content["metadata"]["name"], round_trip_dict["metadata"]["name"])
        self.assertEqual(content["metadata"]["version"], round_trip_dict["metadata"]["version"])
        self.assertEqual(content["spec"]["config"]["provider"], round_trip_dict["spec"]["config"]["provider"])
        self.assertEqual(content["spec"]["config"]["defaultModel"], round_trip_dict["spec"]["config"]["defaultModel"])
        self.assertEqual(content["spec"]["plugins"], round_trip_dict["spec"]["plugins"])

    def test_chatbot_broker_delete(self):
        """Test that the Broker can delete the object."""
        retval = self.broker.apply(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        retval = self.broker.delete(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], f"Chatbot {self.broker.chatbot.name} deleted successfully")

    def test_chatbot_broker_deploy(self):
        """Test that the Broker does not implement a deploy() method."""

        retval = self.broker.deploy(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], f"Chatbot {self.broker.chatbot.name} deployed successfully")

    def test_chatbot_broker_logs(self):
        """Test that the Broker can generate log data."""

        retval = self.broker.logs(request=self.request, kwargs=self.kwargs)
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], f"Chatbot {self.broker.chatbot.name} successfully retrieved logs")

    def test_example_manifest(self):
        """Test that the example manifest is valid."""

        response = self.broker.example_manifest(request=self.request, kwargs=self.kwargs)
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = json.loads(response.content)
        self.assertIsInstance(content, dict)
        self.assertIn("data", content.keys())
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "Chatbot example manifest successfully generated")
        for key in content["data"].keys():
            self.assertIn(key, SAMKeys.all_values())
