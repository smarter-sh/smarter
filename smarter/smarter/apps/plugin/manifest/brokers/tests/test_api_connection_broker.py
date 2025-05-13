# pylint: disable=wrong-import-position
"""Test SAMApiConnectionBroker."""

import json
import os

from django.http import HttpRequest
from waffle.models import Switch

from smarter.apps.account.models import Secret
from smarter.apps.account.tests.factories import factory_secret_teardown, secret_factory
from smarter.apps.plugin.manifest.brokers.api_connection import SAMApiConnectionBroker
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.apps.plugin.models import ApiConnection
from smarter.common.const import SmarterWaffleSwitches
from smarter.lib.django import waffle
from smarter.lib.journal.enum import SmarterJournalThings
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import SAMBrokerErrorNotImplemented

from .base_classes import TestSAMConnectionBrokerBase


class TestSAMApiConnectionBroker(TestSAMConnectionBrokerBase):
    """Test SAMApiConnectionBroker"""

    _model: SAMApiConnection = None
    good_manifest_path: str = None
    waffle_setting: bool = None
    request: HttpRequest = None
    api_key_name: str = None
    api_key_value: str = None
    api_key: Secret = None

    proxy_password_name: str = None
    proxy_password_value: str = None
    proxy_password: Secret = None

    @classmethod
    def setUpClass(cls):
        """
        Set up test fixtures: create an  Secret
        """
        super().setUpClass()
        cls.api_key_name = "test-api-key"
        cls.api_key_value = f"test_api_key_value_{cls.hash_suffix}"
        cls.api_key = secret_factory(
            user_profile=cls.user_profile, name=cls.api_key_name, description="test_api_key", value=cls.api_key_value
        )

        cls.proxy_password_name = "test-proxy-password"
        cls.proxy_password_value = f"test_proxy_password_value_{cls.hash_suffix}"
        cls.proxy_password = secret_factory(
            user_profile=cls.user_profile,
            name=cls.proxy_password_name,
            description="test_proxy_password",
            value=cls.proxy_password_value,
        )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()

        # clean up the api_key secret
        factory_secret_teardown(secret=cls.api_key)
        cls.api_key = None
        cls.api_key_name = None
        cls.api_key_value = None

        # clean up the proxy_password secret
        factory_secret_teardown(secret=cls.proxy_password)
        cls.proxy_password = None
        cls.proxy_password_name = None
        cls.proxy_password_value = None

        # clean up everything else
        cls.good_manifest_path = None
        cls._model = None
        cls.request = None

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.waffle_setting = waffle.switch_is_active(SmarterWaffleSwitches.JOURNAL)
        # temporarily disable the waffle switch for testing
        if self.waffle_setting:
            switch = Switch.objects.get(name=SmarterWaffleSwitches.JOURNAL)
            switch.is_active = False
            switch.save()
        self.good_manifest_path = os.path.join(self.mock_data_path, "api-connection-good.yaml")
        self.valid_manifest_self_check()
        self.request = HttpRequest()

    def tearDown(self):
        """Tear down test fixtures."""
        super().tearDown()
        # restore the waffle switch to its original state
        if self.waffle_setting:
            switch = Switch.objects.get(name=SmarterWaffleSwitches.JOURNAL)
            switch.is_active = True
            switch.save()
        self.request = None
        self._model = None

    @property
    def model(self) -> SAMApiConnection:
        # override to create a pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMApiConnection(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def test_broker_with_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""

        broker = SAMApiConnectionBroker(request=self.request, account=self.account, file_path=self.good_manifest_path)
        self.assertIsInstance(broker, SAMApiConnectionBroker)

        self.assertEqual(type(broker.model_class), type(ApiConnection))
        self.assertEqual(broker.kind, SmarterJournalThings.API_CONNECTION.value)

        # pydantic model
        self.assertIsInstance(broker.manifest, SAMApiConnection)

        # pydantic to django transformer
        self.assertIsInstance(broker.manifest_to_django_orm(), dict)

        # django model
        self.assertIsInstance(broker.api_connection, ApiConnection)

        # journaled response for example manifest
        example_manifest = broker.example_manifest(request=self.request, kwargs={})
        self.assertIsInstance(example_manifest, SmarterJournaledJsonResponse)

        # brokered get() request
        response = broker.get(request=self.request, kwargs={})
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        self.assertEqual(response.status_code, 200)

        response_bytes_value = response.content
        response_json_string = response_bytes_value.decode("utf-8")
        response_json = json.loads(response_json_string)

        self.assertIsInstance(response_json, dict)

        # brokered apply() request
        response = broker.apply(request=self.request, kwargs={})
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        self.assertEqual(response.status_code, 200)
        response_bytes_value = response.content
        response_json_string = response_bytes_value.decode("utf-8")
        response_json = json.loads(response_json_string)
        self.assertIn("ApiConnection test_api_connection applied successfully", response_json["message"])
        self.assertEqual(response_json["thing"], "ApiConnection")

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            broker.chat(request=self.request, kwargs={})

        # brokered describe() request
        response = broker.describe(request=self.request, kwargs={})
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        self.assertEqual(response.status_code, 200)
        print("describe() response content:")
        print(response.content)
        response_bytes_value = response.content
        response_json_string = response_bytes_value.decode("utf-8")
        response_json = json.loads(response_json_string)
        self.assertIsInstance(response_json, dict)
        self.assertIsInstance(response_json["data"], dict)
        self.assertEqual(response_json["thing"], "ApiConnection")

        # brokered delete() request
        response = broker.delete(request=self.request, kwargs={})
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        self.assertEqual(response.status_code, 200)
        response_bytes_value = response.content
        response_json_string = response_bytes_value.decode("utf-8")
        response_json = json.loads(response_json_string)
        self.assertIn("ApiConnection test_api_connection deleted successfully", response_json["message"])
        self.assertEqual(response_json["thing"], "ApiConnection")

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            broker.deploy(request=self.request, kwargs={})

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            broker.undeploy(request=self.request, kwargs={})

        with self.assertRaises(SAMBrokerErrorNotImplemented):
            broker.logs(request=self.request, kwargs={})
