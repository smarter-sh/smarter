"""Test abstract Broker class"""

import json
import logging
import os
from typing import Optional

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.common.const import PYTHON_ROOT
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    BrokerNotImplemented,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    SAMBrokerReadOnlyError,
)
from smarter.lib.manifest.models import AbstractSAMBase

from .abstractbroker_test_class import SAMTestBroker


logger = logging.getLogger(__name__)


# pylint: disable=too-many-public-methods
class TestAbstractBrokerClass(TestAccountMixin):
    """
    Test abstract Broker class coverage gaps.
    531
    """

    good_manifest_path: Optional[str] = None
    good_manifest_text: Optional[str] = None
    broker: Optional[SAMTestBroker] = None

    @classmethod
    def setUpClass(cls) -> None:
        """Set up test fixtures."""
        super().setUpClass()
        path = os.path.join(PYTHON_ROOT, "smarter", "apps", "api", "v1", "cli", "tests", "data")
        cls.good_manifest_path = os.path.join(path, "good-plugin-manifest.yaml")
        cls.good_manifest_text = cls.get_readonly_yaml_file(cls.good_manifest_path)  # type: ignore[assignment]

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        client = Client()
        client.force_login(self.non_admin_user)
        response = client.get("/")
        request = response.wsgi_request

        if not hasattr(request, "user"):
            raise ValueError("Request does not have a user attribute")

        self.broker = SAMTestBroker(
            request,
            manifest=self.good_manifest_text,
            kind=SmarterJournalThings.STATIC_PLUGIN.value,
        )

    def test_SAMBrokerError(self) -> None:
        # 58-61,
        try:
            raise SAMBrokerError(
                message="Test error message",
                thing=SmarterJournalThings.STATIC_PLUGIN,
                command=SmarterJournalCliCommands.APPLY,
            )
        except SAMBrokerError as e:
            msg = e.get_formatted_err_message
            self.assertEqual(msg, "Smarter API Plugin manifest broker: apply() unidentified error.  Test error message")

    def test_SAMBrokerReadOnlyError(self) -> None:
        # 69-72,
        try:
            raise SAMBrokerReadOnlyError(
                message="Test error message",
                thing=SmarterJournalThings.STATIC_PLUGIN,
                command=SmarterJournalCliCommands.APPLY,
            )
        except SAMBrokerReadOnlyError as e:
            msg = e.get_formatted_err_message
            self.assertEqual(msg, "Smarter API Plugin manifest broker: apply() read-only error.  Test error message")

    def test_SAMBrokerErrorNotImplemented(self) -> None:
        try:
            raise SAMBrokerErrorNotImplemented(
                message="Test error message",
                thing=SmarterJournalThings.STATIC_PLUGIN,
                command=SmarterJournalCliCommands.APPLY,
            )
        except SAMBrokerErrorNotImplemented as e:
            msg = e.get_formatted_err_message
            self.assertEqual(
                msg, "Smarter API Plugin manifest broker: apply() not implemented error.  Test error message"
            )

    def test_SAMBrokerErrorNotReady(self) -> None:
        # 91-94,
        try:
            raise SAMBrokerErrorNotReady(
                message="Test error message",
                thing=SmarterJournalThings.STATIC_PLUGIN,
                command=SmarterJournalCliCommands.APPLY,
            )
        except SAMBrokerErrorNotReady as e:
            msg = e.get_formatted_err_message
            self.assertEqual(msg, "Smarter API Plugin manifest broker: apply() not ready error.  Test error message")

    def test_SAMBrokerErrorNotFound(self) -> None:
        # 102-105,
        try:
            raise SAMBrokerErrorNotFound(
                message="Test error message",
                thing=SmarterJournalThings.STATIC_PLUGIN,
                command=SmarterJournalCliCommands.APPLY,
            )
        except SAMBrokerErrorNotFound as e:
            msg = e.get_formatted_err_message
            self.assertEqual(msg, "Smarter API Plugin manifest broker: apply() not found error.  Test error message")

    def test_uri(self) -> None:
        # 200-212,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        self.assertEqual(self.broker.uri, "http://testserver/")

    def test_is_valid(self) -> None:
        # 216,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        self.assertTrue(self.broker.is_valid)

    def test_kind(self):
        # 219,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        self.assertEqual(self.broker.kind, SmarterJournalThings.STATIC_PLUGIN.value)

    def test_str_(self) -> None:
        # 248,
        self.assertEqual(str(self.broker), "smarter.sh/v1 Plugin Broker")

    def test_model_class(self) -> None:
        # 255
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.model_class
        except SAMBrokerErrorNotImplemented as e:
            self.assertEqual(
                e.get_formatted_err_message, "Smarter API Plugin manifest broker: None() not implemented error."
            )

    def test_manifest(self) -> None:
        # 265-275,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        self.assertIsNotNone(self.broker.manifest)
        self.assertIsInstance(self.broker.manifest, AbstractSAMBase)

    def test_apply(self) -> None:
        # 284,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.apply(request=self.broker.request, kwargs=None)
        except SAMBrokerReadOnlyError as e:
            self.assertEqual(
                e.get_formatted_err_message, "Smarter API Plugin manifest broker: apply() not implemented error."
            )

    def test_chat(self) -> None:
        # 293,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.chat(request=self.broker.request, kwargs=None)
        except SAMBrokerErrorNotImplemented as e:
            self.assertEqual(
                e.get_formatted_err_message,
                "Smarter API Plugin manifest broker: chat() not implemented error.  chat() not implemented",
            )

    def test_describe(self) -> None:
        # 300,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        logger.info("Testing describe method of SAMTestBroker")
        logger.info("Broker: %s", self.broker)
        logger.info("User: %s %s", self.broker.request.user, self.non_admin_user)
        logger.info("Account: %s %s", self.broker.account, self.account)
        logger.info("UserProfile: %s %s", self.broker.user_profile, self.non_admin_user_profile)

        try:
            self.broker.describe(request=self.broker.request, kwargs=None)
        except SAMBrokerErrorNotImplemented as e:
            self.assertIn(
                "Smarter API Plugin manifest broker: describe() not implemented error.", e.get_formatted_err_message
            )

    def test_delete(self) -> None:
        # 307,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.delete(request=self.broker.request, kwargs=None)
        except SAMBrokerErrorNotImplemented as e:
            self.assertEqual(
                e.get_formatted_err_message,
                "Smarter API Plugin manifest broker: delete() not implemented error.  delete() not implemented",
            )

    def test_deploy(self) -> None:
        # 314,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.deploy(request=self.broker.request, kwargs=None)
        except SAMBrokerErrorNotImplemented as e:
            self.assertEqual(
                e.get_formatted_err_message,
                "Smarter API Plugin manifest broker: deploy() not implemented error.  deploy() not implemented",
            )

    def test_example_manifest(self) -> None:
        # 321,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.example_manifest(request=self.broker.request, kwargs=None)
        except SAMBrokerErrorNotImplemented as e:
            self.assertEqual(
                e.get_formatted_err_message,
                "Smarter API Plugin manifest broker: example_manifest() not implemented error.  example_manifest() not implemented",
            )

    def test_get(self) -> None:
        # 330,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.get(request=self.broker.request, kwargs=None)
        except SAMBrokerErrorNotImplemented as e:
            self.assertEqual(
                e.get_formatted_err_message,
                "Smarter API Plugin manifest broker: get() not implemented error.  get() not implemented",
            )

    def test_logs(self) -> None:
        # 337,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.logs(request=self.broker.request, kwargs=None)
        except SAMBrokerErrorNotImplemented as e:
            self.assertEqual(
                e.get_formatted_err_message,
                "Smarter API Plugin manifest broker: logs() not implemented error.  logs() not implemented",
            )

    def test_undeploy(self) -> None:
        # 344,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            self.broker.undeploy(request=self.broker.request, kwargs=None)
        except SAMBrokerErrorNotImplemented as e:
            self.assertEqual(
                e.get_formatted_err_message,
                "Smarter API Plugin manifest broker: undeploy() not implemented error.  undeploy() not implemented",
            )

    def test_json_response_err_readlonly(self) -> None:
        # 387-398,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        response = self.broker.json_response_err_readonly(command=SmarterJournalCliCommands.APPLY)
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        response_dict = json.loads(response.content)
        self.assertIn("error", response_dict.keys())
        self.assertEqual(response_dict["error"]["errorClass"], "SAMBrokerReadOnlyError")

    def test_json_response_err_notimplemented(self) -> None:
        # 404-415,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        response = self.broker.json_response_err_notimplemented(command=SmarterJournalCliCommands.APPLY)
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        response_dict = json.loads(response.content)
        self.assertIn("error", response_dict.keys())
        self.assertEqual(response_dict["error"]["errorClass"], "SAMBrokerErrorNotImplemented")

    def test_json_response_err_notready(self) -> None:
        # 421-432,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        response = self.broker.json_response_err_notready(command=SmarterJournalCliCommands.APPLY)
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        response_dict = json.loads(response.content)
        self.assertIn("error", response_dict.keys())
        self.assertEqual(response_dict["error"]["errorClass"], "SAMBrokerErrorNotReady")

    def test_json_response_err_notfound(self) -> None:
        # 440-451,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        response = self.broker.json_response_err_notfound(command=SmarterJournalCliCommands.APPLY)
        self.assertIsInstance(response, SmarterJournaledJsonResponse)
        response_dict = json.loads(response.content)
        self.assertIn("error", response_dict.keys())
        self.assertEqual(response_dict["error"]["errorClass"], "SAMBrokerErrorNotFound")

    def test_json_response_err(self) -> None:
        # 460,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        try:
            raise SAMBrokerReadOnlyError(
                message="Test error message",
                thing=SmarterJournalThings.STATIC_PLUGIN,
                command=SmarterJournalCliCommands.APPLY,
            )
        except SAMBrokerReadOnlyError as e:
            response = self.broker.json_response_err(command=SmarterJournalCliCommands.APPLY, e=e)
            self.assertIsInstance(response, SmarterJournaledJsonResponse)
            response_dict = json.loads(response.content)
            self.assertIn("error", response_dict.keys())
            self.assertEqual(response_dict["error"]["errorClass"], "SAMBrokerReadOnlyError")

    def test_set_and_verify_name_param(self) -> None:
        # 473,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        self.broker.set_and_verify_name_param()

    def test_camel_to_snake(self) -> None:
        # 501,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        d = {
            "testCamelCase": "test_camel_case",
            "testCamelCase2": "test_camel_case2",
            "testCamelCase3": "test_camel_case3",
        }
        d_result = {
            "test_camel_case": "test_camel_case",
            "test_camel_case2": "test_camel_case2",
            "test_camel_case3": "test_camel_case3",
        }
        camel_to_snake = self.broker.camel_to_snake(data=d)
        self.assertEqual(camel_to_snake, d_result)

    def test_snake_to_camel(self) -> None:
        # 516,
        if not self.broker:
            raise ValueError("Broker is not initialized")
        d = {
            "test_camel_case": "test_camel_case",
            "test_camel_case2": "test_camel_case2",
            "test_camel_case3": "test_camel_case3",
        }
        d_result = {
            "testCamelCase": "test_camel_case",
            "testCamelCase2": "test_camel_case2",
            "testCamelCase3": "test_camel_case3",
        }
        snake_to_camel = self.broker.snake_to_camel(data=d)
        self.assertEqual(snake_to_camel, d_result)

    def test_BrokerNotImplemented(self) -> None:
        # 531,
        try:
            BrokerNotImplemented()
        except SAMBrokerErrorNotImplemented:
            pass
