"""Test OrchestratorApiBaseViewSet."""

import os

from django.http import HttpRequest
from django.test import RequestFactory
from rest_framework.test import APIClient

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.orchestrator.manifest.brokers.orchestrator import (
    SAMOrchestratorBroker,
)
from smarter.apps.plugin.plugin.tests.base_classes import mock_remote_skills
from smarter.apps.plugin.utils import add_example_plugins
from smarter.common.utils import get_readonly_yaml_file
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.loader import SAMLoader

from ..base import OrchestratorApiBaseViewSet

HERE = os.path.abspath(os.path.dirname(__file__))


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ORCHESTRATOR])


# pylint: disable=too-many-instance-attributes
class TestOrchestratorApiBaseViewSet(TestAccountMixin):
    """Test SAM Orchestrator Broker."""

    # pylint: disable=W0212
    @classmethod
    def create_generic_request(cls, url: str) -> HttpRequest:
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
        request: HttpRequest = factory.post(path=url, data=json_data, content_type="application/json")
        return request

    @classmethod
    def setUpClass(cls):
        """Set up test fixtures."""
        super().setUpClass()
        config_path = os.path.join(HERE, "data/orchestrator.yaml")
        cls.manifest = get_readonly_yaml_file(config_path)
        cls.loader = SAMLoader(manifest=cls.manifest)

        cls.request = cls.create_generic_request("/anywhere/")

        cls.request.user = cls.admin_user
        cls.client = APIClient()
        cls.client.force_login(cls.admin_user)
        cls.kwargs = {}

        # name: test_orchestrator
        cls.broker = SAMOrchestratorBroker(
            request=cls.request,
            account=cls.account,
            loader=cls.loader,
        )

        # Add example plugins to the user profile
        with mock_remote_skills():
            add_example_plugins(user_profile=cls.user_profile)

        # the LLMClient that the manifest's harness refers to by name
        cls.harness_llmclient, _ = LLMClient.objects.get_or_create(
            name="test_orchestrator_harness",
            user_profile=cls.user_profile,
            defaults={"description": "Test Orchestrator harness", "version": "1.0.0"},
        )

        cls.broker.apply(request=cls.request, kwargs=cls.kwargs)

    @classmethod
    def tearDownClass(cls):
        """Tear down test fixtures."""
        try:
            cls.broker.delete(request=cls.request, kwargs=cls.kwargs)
        # pylint: disable=W0718
        except Exception:
            pass
        try:
            cls.harness_llmclient.delete()
        # pylint: disable=W0718
        except Exception:
            pass
        finally:
            super().tearDownClass()

    def test_base_class_properties(self):
        base_class = OrchestratorApiBaseViewSet(request=self.request)

        # invoke dispatch method in order to set our class properties
        base_class.dispatch(request=self.request, name=self.broker.orchestrator.name)  # type: ignore

        logger.debug("test_base_class_properties() request=%s name=%s", self.request, self.broker.orchestrator.name)  # type: ignore
