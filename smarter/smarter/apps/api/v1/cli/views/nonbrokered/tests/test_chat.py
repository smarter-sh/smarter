"""Test Api v1 CLI non-brokered prompt command."""

import secrets
from http import HTTPStatus
from unittest import mock
from urllib.parse import urlencode

import httpx
import openai

from smarter.apps.api.v1.cli.tests.base_class import ApiV1CliTestBase
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.cli.views.nonbrokered.prompt import ApiV1CliPromptApiView
from smarter.apps.llmclient.models import LLMClient
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.shortcuts import reverse
from smarter.lib.journal.enum import (
    SCLIResponseMetadata,
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
    SmarterJournalThings,
)

CREATE_PATCH = (
    "smarter.apps.provider.services.text_completion.lib.openai_compatible_chat_provider.openai.chat.completions.create"
)
# Celery tasks that write rows that refer to the prompt, or charge for it. Celery is not eager in tests, so
# unpatched, they run in the live worker, which can write a row while the test deletes the prompt.
PROMPT_TASK_PATCHES = (
    "smarter.apps.prompt.receivers.create_prompt_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_tool_call_history",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_prompt_plugin_usage",
    "smarter.apps.provider.services.text_completion.lib.mixins.create_charge",
)


def model_not_found(model: str) -> openai.NotFoundError:
    """A 404 from OpenAI for a model that does not exist."""
    request = httpx.Request("POST", "https://api.openai.com/v1/chat/completions")
    body = {
        "message": f"The model `{model}` does not exist or you do not have access to it.",
        "code": "model_not_found",
    }
    return openai.NotFoundError("not found", response=httpx.Response(404, request=request), body=body)


class TestApiCliV1Chat(ApiV1CliTestBase):
    """
    Test Api v1 CLI non-brokered prompt command.

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def setUp(self):
        super().setUp()
        self.kwargs = {"name": self.name}

        self.query_params = urlencode({"uid": self.uid})

        self.llmclient = self.llmclient_factory()

    def tearDown(self):
        if self.llmclient:
            self.llmclient.delete()
        super().tearDown()

    def llmclient_factory(self):
        llmclient = LLMClient.objects.create(
            name=self.name,
            user_profile=self.user_profile,
            description="Test LLMClient",
            version="1.0.0",
            subdomain=None,
            custom_domain=None,
            deployed=False,
            app_name="Smarter",
            app_assistant="Smarty Pants",
            app_welcome_message="Welcome to Smarter!",
        )
        return llmclient

    def validate_response(self, response: dict) -> None:
        self.assertIsInstance(response, dict)
        self.assertEqual(response[SmarterJournalApiResponseKeys.API], SmarterApiVersions.V1)
        self.assertEqual(
            response[SmarterJournalApiResponseKeys.METADATA][SmarterJournalApiResponseKeys.THING],
            SmarterJournalThings.PROMPT.value,
        )
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.DATA], dict)
        self.assertIsInstance(response[SmarterJournalApiResponseKeys.METADATA], dict)

    def validate_data(self, data: dict) -> None:
        config_fields = [
            "request",
            "response",
        ]
        for field in config_fields:
            assert field in data.keys(), f"{field} not found in data keys: {data.keys()}"

    def test_chat(self) -> None:
        """Test prompt command."""

        data = {"prompt": "Hello, World!"}
        path = reverse(self.namespace + ApiV1CliReverseViews.prompt, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params, data=data)
        self.assertEqual(status, HTTPStatus.OK)
        self.validate_response(response)
        data = response[SmarterJournalApiResponseKeys.DATA]
        self.validate_data(data=data)
        metadata = response[SmarterJournalApiResponseKeys.METADATA]
        metadata[SCLIResponseMetadata.COMMAND] = SmarterJournalCliCommands.PROMPT.value

    def test_chat_provider_error(self) -> None:
        """Test that the LLM provider's error response is returned with its status and message."""
        self.llmclient.default_model = "gpt-nonexistent-9000"
        self.llmclient.save()
        for target in PROMPT_TASK_PATCHES:
            patcher = mock.patch(target)
            patcher.start()
            self.addCleanup(patcher.stop)
        path = reverse(self.namespace + ApiV1CliReverseViews.prompt, kwargs=self.kwargs)
        # a new session, rather than the class's, whose cached prompt may belong to a deleted llmclient.
        query_params = urlencode({"uid": secrets.token_hex(32)})
        with mock.patch(CREATE_PATCH, side_effect=model_not_found("gpt-nonexistent-9000")):
            response, status = self.get_response(path=f"{path}?{query_params}", data={"prompt": "Hello"})
        self.assertEqual(status, HTTPStatus.NOT_FOUND, response)
        self.assertEqual(
            response[SmarterJournalApiResponseKeys.ERROR]["description"],
            "The model `gpt-nonexistent-9000` does not exist or you do not have access to it.",
        )

    def test_prompt_error_message(self) -> None:
        """Test the error message of a prompt's error response."""
        body = '{"error": {"status": 400, "message": "max_tokens is too large"}}'
        chat_response = {SmarterJournalApiResponseKeys.DATA: {"statusCode": 400, "body": body}}
        self.assertEqual(ApiV1CliPromptApiView.prompt_error_message(chat_response), "max_tokens is too large")
        chat_response = {SmarterJournalApiResponseKeys.DATA: {"statusCode": 502}}
        self.assertIn("502", ApiV1CliPromptApiView.prompt_error_message(chat_response))
