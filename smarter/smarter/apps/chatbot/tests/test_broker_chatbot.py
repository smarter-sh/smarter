"""Test SAM Chatbot Broker"""

import json
import os
import unittest
from http import HTTPStatus

import yaml
from django.http import JsonResponse

from smarter.apps.account.tests.factories import admin_user_factory, admin_user_teardown
from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker
from smarter.apps.chatbot.manifest.models.chatbot.model import SAMChatbot
from smarter.common.utils import dict_is_contained_in
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.manifest.loader import SAMLoader
from smarter.lib.unittest.utils import get_readonly_yaml_file


HERE = os.path.abspath(os.path.dirname(__file__))


class TestSAMChatbotBroker(unittest.TestCase):
    """Test SAM Chatbot Broker"""

    def setUp(self):
        """Set up test fixtures."""
        self.user, self.account, self.user_profile = admin_user_factory()

        config_path = os.path.join(HERE, "data/chatbot.yaml")
        self.manifest = get_readonly_yaml_file(config_path)
        self.broker = SAMChatbotBroker(account=self.account, manifest=self.manifest)

    def tearDown(self):
        """Tear down test fixtures."""
        admin_user_teardown(self.user, self.account, self.user_profile)

    def test_chatbot_broker_apply(self):
        """Test that the Broker can apply the manifest."""
        retval = self.broker.apply()
        content = json.loads(retval.content.decode())
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "Chatbot TestChatbot applied successfully")

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

        retval = self.broker.apply()
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        # generate the manifest
        retval = self.broker.describe()
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        # transform the json content to a yaml manifest
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        content = content["data"]  # the manifest is loaded into the 'data' key
        content.pop("status")  # status is read-only
        manifest = yaml.dump(content)

        # load the yaml manifest into a SAMLoader object
        loader = SAMLoader(manifest=manifest)

        # create a pydantic model from the loader
        pydantic_model = SAMChatbot(**loader.pydantic_model_dump())

        # dump the pydantic model to a dictionary
        round_trip_dict = pydantic_model.model_dump()

        # assert that everything in content is in round_trip_dict
        self.assertTrue(dict_is_contained_in(content, round_trip_dict))

    def test_chatbot_broker_delete(self):
        """Test that the Broker can delete the object."""
        retval = self.broker.apply()
        self.assertEqual(retval.status_code, HTTPStatus.OK)

        retval = self.broker.delete()
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "Chatbot TestChatbot deleted successfully")

    def test_chatbot_broker_deploy(self):
        """Test that the Broker does not implement a deploy() method."""

        retval = self.broker.deploy()
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "Chatbot TestChatbot deployed successfully")

    def test_chatbot_broker_logs(self):
        """Test that the Broker can generate log data."""

        retval = self.broker.logs()
        self.assertEqual(retval.status_code, HTTPStatus.OK)
        content = json.loads(retval.content.decode())
        self.assertIsInstance(content, dict)
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "Chatbot TestChatbot successfully retrieved logs")

    def test_example_manifest(self):
        """Test that the example manifest is valid."""

        response = self.broker.example_manifest()
        self.assertIsInstance(response, JsonResponse)
        self.assertEqual(response.status_code, HTTPStatus.OK)

        content = json.loads(response.content)
        self.assertIsInstance(content, dict)
        self.assertIn("data", content.keys())
        self.assertIn("message", content.keys())
        self.assertEqual(content["message"], "Chatbot example manifest successfully generated")
        for key in content["data"].keys():
            self.assertIn(key, SAMKeys.all_values())
