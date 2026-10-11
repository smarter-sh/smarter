"""Test :mod:`smarter.apps.prompt.contract.builders`."""

import json
import os
from http import HTTPStatus

from django.test import RequestFactory

from smarter.apps.prompt.contract.builders import (
    PromptChatApiErrorLLMProvider,
    PromptChatApiErrorNotFound,
    chat_error_response,
    prompt_result_v2,
    requested_contract,
    without_diagnostics,
)
from smarter.apps.prompt.contract.const import CHAT_CONTRACT_V1, CHAT_CONTRACT_V2
from smarter.apps.prompt.contract.models import PromptChatApiPromptResponse
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.typing import SmarterDictType
from smarter.lib.unittest.base_classes import SmarterTestBase

HERE = os.path.abspath(os.path.dirname(__file__))


class TestContractBuilders(SmarterTestBase):
    """Test the builders of the Smarter Chat api contract's responses."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.responses = cls.get_readonly_yaml_file(os.path.join(HERE, "data", "prompt_responses.yaml"))

    def lambda_response(self, name: str) -> SmarterDictType:
        """A prompt's Lambda style result from the fixtures, with its body as a JSON string."""
        response = dict(self.responses[name])
        response["body"] = json.dumps(response["body"])
        return response

    def test_requested_contract(self):
        factory = RequestFactory()
        self.assertEqual(requested_contract(None), CHAT_CONTRACT_V2)
        # version 2 is the default.
        self.assertEqual(requested_contract(factory.post("/config/")), CHAT_CONTRACT_V2)
        for header in ("chat-contract-v2", "something-else, Chat-Contract-V2 ", "chat-contract-v1, chat-contract-v2"):
            with self.subTest(header=header):
                request = factory.post("/config/", HTTP_X_SMARTER_CAPABILITIES=header)
                self.assertEqual(requested_contract(request), CHAT_CONTRACT_V2)
        request = factory.post("/config/", HTTP_X_SMARTER_CAPABILITIES="chat-contract-v1")
        self.assertEqual(requested_contract(request), CHAT_CONTRACT_V1)
        request = factory.post("/config/", HTTP_X_SMARTER_CAPABILITIES="chat-contract-v3")
        self.assertEqual(requested_contract(request), CHAT_CONTRACT_V2)

    def test_requested_contract_of_smarter_chat_up_to_0_7(self):
        """Smarter Chat without a contract capability is a version up to 0.7, which reads version 1 only."""
        factory = RequestFactory()
        request = factory.post("/config/", HTTP_X_SMARTER_CLIENT="@smarter.sh/ui-chat")
        self.assertEqual(requested_contract(request), CHAT_CONTRACT_V1)
        request = factory.post(
            "/config/", HTTP_X_SMARTER_CLIENT="@smarter.sh/ui-chat", HTTP_X_SMARTER_CAPABILITIES="chat-contract-v2"
        )
        self.assertEqual(requested_contract(request), CHAT_CONTRACT_V2)

    def test_chat_error_response_has_no_stack_trace(self):
        response = chat_error_response(
            RequestFactory().post("/config/"),
            PromptChatApiErrorNotFound("LLMClient not found."),
            thing=SmarterJournalThings(SmarterJournalThings.PROMPT_CONFIG),
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.PROMPT_CONFIG),
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        error = json.loads(response.content)["error"]
        self.assertEqual(error["errorClass"], "PromptChatApiErrorNotFound")
        self.assertEqual(error["description"], "LLMClient not found.")
        self.assertEqual(error["status"], HTTPStatus.NOT_FOUND)
        self.assertNotIn("stacktrace", error)

    def test_without_diagnostics(self):
        success = json.loads(without_diagnostics(self.lambda_response("success"))["body"])
        self.assertNotIn("first_iteration", success["smarter"])
        self.assertNotIn("second_iteration", success["smarter"])
        self.assertEqual(len(success["smarter"]["messages"]), 2)
        self.assertNotIn("secret system prompt", json.dumps(success))
        self.assertNotIn("metadata", success)

        failure = json.loads(without_diagnostics(self.lambda_response("failure"))["body"])
        self.assertNotIn("first_iteration", failure["response"]["smarter"])
        self.assertEqual(failure["error"]["status"], 401)

    def test_without_diagnostics_leaves_anything_else_as_is(self):
        for response in (None, "text", {"statusCode": 200}, {"body": "not json"}, {"body": json.dumps(["a"])}):
            with self.subTest(response=response):
                self.assertEqual(without_diagnostics(response), response)
        no_smarter = {"body": json.dumps({"id": "x"})}
        self.assertEqual(json.loads(without_diagnostics(no_smarter)["body"]), {"id": "x"})

    def test_prompt_result_v2_of_a_successful_prompt(self):
        data, error, status = prompt_result_v2(self.lambda_response("success"))
        self.assertIsNone(error)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertEqual(data["contract"], CHAT_CONTRACT_V2)
        self.assertEqual([message["role"] for message in data["messages"]], ["smarter", "assistant"])
        self.assertEqual(data["plugins"], ["stackademy_sql"])
        self.assertEqual(data["tools"], ["smarter_plugin_0000000016"])
        self.assertEqual(data["completion"]["choices"][0]["finish_reason"], "stop")
        self.assertNotIn("smarter", data["completion"])
        self.assertNotIn("secret system prompt", json.dumps(data))
        PromptChatApiPromptResponse.model_validate({"data": data, "api": "smarter.sh/v1", "metadata": {}})

    def test_prompt_result_v2_of_a_failed_prompt(self):
        data, error, status = prompt_result_v2(self.lambda_response("failure"))
        self.assertEqual(status, HTTPStatus.UNAUTHORIZED)
        self.assertEqual(error["errorClass"], PromptChatApiErrorLLMProvider.__name__)
        self.assertEqual(error["description"], "Incorrect API key provided.")
        self.assertEqual(data["status"], HTTPStatus.UNAUTHORIZED)
        self.assertEqual(data["messages"][0]["role"], "smarter_error")
        PromptChatApiPromptResponse.model_validate(
            {"data": data, "error": error, "api": "smarter.sh/v1", "metadata": {}}
        )

    def test_prompt_result_v2_of_an_unexpected_result(self):
        data, error, status = prompt_result_v2({"statusCode": 502, "body": "not json"})
        self.assertEqual(status, 502)
        self.assertEqual(error["description"], "The prompt failed with http status 502.")
        self.assertEqual(data["messages"], [])
        self.assertIsNone(data["completion"])

        data, error, status = prompt_result_v2(None)
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsNone(error)
        self.assertIsNone(data["completion"])
