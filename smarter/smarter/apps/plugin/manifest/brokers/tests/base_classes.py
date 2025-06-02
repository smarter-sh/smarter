"""Test base classes for the plugin API tests."""

import json
import os

from django.test import Client

from smarter.apps.plugin.tests.base_classes import (
    TestConnectionBase,
    TestPluginBase,
    TestPluginClassBase,
)
from smarter.lib.drf.models import SmarterAuthToken

from .factories import create_generic_request


HERE = os.path.abspath(os.path.dirname(__file__))


# pylint: disable=W0223
class TestSAMBrokerMixin(TestPluginClassBase):
    """Test SAMStaticPluginBrokerBase"""

    @property
    def good_manifest_path(self) -> str:
        raise NotImplementedError("Subclasses must implement this property")

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        instance = cls()

        cls.token_record, cls.token_key = SmarterAuthToken.objects.create(
            name=instance.admin_user.username,
            user=instance.admin_user,
            description=instance.admin_user.username,
        )

    @classmethod
    def tearDownClass(cls) -> None:
        super().tearDownClass()
        instance = cls()
        try:
            instance.token_record.delete()
        except SmarterAuthToken.DoesNotExist:
            pass

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.mock_data_path = os.path.join(HERE, "mock_data")
        self.request = create_generic_request()
        self.client = Client()
        self.client.force_login(self.admin_user)

    def tearDown(self):
        """Clean up test fixtures."""
        self.request = None
        self.client = None
        super().tearDown()

    def valid_manifest_self_check(self):
        """
        Test that we can instantiate a valid Plugin manifest without errors.
        This does not need to be exhaustive, as we already have comprehensive tests
        for the manifest itself in smarter.apps.plugin.tests.

        This is intended to be added to setUp() in the child classes:
        def setUp(self):
            super().setUp()
            self.good_manifest_path = os.path.join(self.mock_data_path, "static-plugin-good.yaml")
            self.valid_manifest_self_check()

        """
        self.load_manifest(filename=self.good_manifest_path)
        self.assertIsNotNone(self.model)

    def get_response(self, path, manifest: str = None, data: dict = None) -> tuple[dict[str, any], int]:
        """
        Prepare and get a response from an api/v1/ endpoint.
        """
        client = Client()
        headers = {"Authorization": f"Token {self.token_key}"}
        response_json = None

        if manifest:
            response = client.post(path=path, data=manifest, content_type="application/json", **headers)
        elif data:
            response = client.post(path=path, data=data, content_type="application/json", **headers)
        else:
            response = client.post(path=path, content_type="application/json", data=None, **headers)
        response_content = response.content.decode("utf-8")
        try:
            response_json = json.loads(response_content)
        except json.JSONDecodeError:
            # If the response is not JSON, return the raw content
            response_json = response_content
        if isinstance(response_json, str):
            # If the response is a string, try to parse it as JSON
            try:
                response_json = json.loads(response_json)
            except json.JSONDecodeError:
                # If it still fails, return the string as is
                pass
        if isinstance(response_json, dict):
            # If the response is a dictionary, check for the "error" key
            if "error" in response_json:
                # If the error key is present, raise an exception with the error message
                # pylint: disable=W0719
                raise Exception(f"Error in response: {response_json['error']}")
        elif isinstance(response_json, list):
            # If the response is a list, check if it contains any dictionaries
            for item in response_json:
                if isinstance(item, dict) and "error" in item:
                    # If any dictionary in the list has an "error" key, raise an exception
                    # pylint: disable=W0719
                    raise Exception(f"Error in response: {item['error']}")
        return response_json, response.status_code


class TestSAMPluginBrokerBase(TestPluginBase, TestSAMBrokerMixin):
    """Test SAMStaticPluginBrokerBase"""


class TestSAMConnectionBrokerBase(TestConnectionBase, TestSAMBrokerMixin):
    """Test SAMConnectionBrokerBase"""
