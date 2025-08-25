# pylint: disable=wrong-import-position
"""Test SAMApiConnectionBroker."""

import os
from typing import Optional

from django.http import HttpRequest
from waffle.models import Switch

from smarter.apps.account.models import Secret
from smarter.apps.account.tests.factories import factory_secret_teardown, secret_factory
from smarter.apps.plugin.manifest.brokers.api_connection import SAMApiConnectionBroker
from smarter.apps.plugin.manifest.models.api_connection.model import SAMApiConnection
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .base_classes import TestSAMConnectionBrokerBase


class TestSAMApiConnectionBroker(TestSAMConnectionBrokerBase):
    """Test SAMApiConnectionBroker"""

    _model: Optional[SAMApiConnection] = None
    good_manifest_path: Optional[str] = None
    waffle_setting: bool = False
    request: HttpRequest
    api_key_name: Optional[str] = None
    api_key_value: Optional[str] = None
    api_key: Optional[Secret] = None

    proxy_password_name: Optional[str] = None
    proxy_password_value: Optional[str] = None
    proxy_password: Optional[Secret] = None

    @classmethod
    def setUpClass(cls):
        """
        Set up test fixtures: create an  Secret
        """
        super().setUpClass()
        cls.api_key_name = "test_api_key"
        cls.api_key_value = f"test-api-key-value-{cls.hash_suffix}"
        cls.api_key = secret_factory(
            user_profile=cls.user_profile, name=cls.api_key_name, description="test api key", value=cls.api_key_value
        )

        cls.proxy_password_name = "test_proxy_password"
        cls.proxy_password_value = f"test-proxy-password-value-{cls.hash_suffix}"
        cls.proxy_password = secret_factory(
            user_profile=cls.user_profile,
            name=cls.proxy_password_name,
            description="test proxy password",
            value=cls.proxy_password_value,
        )

    @classmethod
    def tearDownClass(cls):

        try:
            # clean up the api_key secret
            factory_secret_teardown(secret=cls.api_key)  # pylint: disable=E1101
            cls.api_key = None
            cls.api_key_name = None
            cls.api_key_value = None

            # clean up the proxy_password secret
            factory_secret_teardown(secret=cls.proxy_password)  # type: ignore[E1101]
            cls.proxy_password = None
            cls.proxy_password_name = None
            cls.proxy_password_value = None

            # clean up everything else
            cls.good_manifest_path = None
            cls._model = None
            cls.request = None
        # pylint: disable=W0718
        except Exception:
            pass
        finally:
            super().tearDownClass()

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.waffle_setting = waffle.switch_is_active(SmarterWaffleSwitches.JOURNAL)
        # temporarily disable the waffle switch for testing
        if self.waffle_setting:
            switch = Switch.objects.get(name=SmarterWaffleSwitches.JOURNAL)
            switch.is_active = False  # type: ignore[assignment]
            switch.save()
        self.good_manifest_path = os.path.join(self.mock_data_path, "api-connection-good.yaml")
        self.valid_manifest_self_check()
        self.request = HttpRequest()

    def tearDown(self):
        """Tear down test fixtures."""
        # restore the waffle switch to its original state
        if self.waffle_setting:
            switch = Switch.objects.get(name=SmarterWaffleSwitches.JOURNAL)
            switch.is_active = True  # type: ignore[assignment]
            switch.save()
        self.request = None
        self._model = None
        super().tearDown()

    @property
    def model(self) -> Optional[SAMApiConnection]:
        # override to create a pydantic model from the loader
        if not self._model and self.loader:
            self._model = SAMApiConnection(**self.loader.pydantic_model_dump())
            self.assertIsNotNone(self._model)
        return self._model

    def test_broker_with_valid_manifest(self):
        """Test valid file path and that we can instantiate without errors"""

        broker = SAMApiConnectionBroker(request=self.request, account=self.account, file_path=self.good_manifest_path)
        self.assertIsInstance(broker, SAMApiConnectionBroker)
