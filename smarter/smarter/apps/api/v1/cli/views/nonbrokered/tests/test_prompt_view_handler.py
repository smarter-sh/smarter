"""
Unit tests of ApiV1CliPromptApiView's initial(), handler() and post() error branches.

The prompt config and llmclient views it calls are replaced, as are its request-derived properties.
"""

from contextlib import ExitStack
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, patch

from django.http import HttpResponse, JsonResponse, QueryDict
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.cli.views.base import APIV1CLIViewError, CliBaseApiView
from smarter.apps.api.v1.cli.views.nonbrokered.prompt import (
    APIV1CLIChatViewError,
    ApiV1CliPromptApiView,
)
from smarter.lib import json

MODULE = "smarter.apps.api.v1.cli.views.nonbrokered.prompt"
SESSION_KEY = "9913baee675fb6618519c478bd4805c4ff9eeaab710e4f127ba67bb1eb442126"


class TestPromptViewHandler(TestAccountMixin):
    """Test how ApiV1CliPromptApiView handles failures of the views it calls."""

    def setUp(self):
        super().setUp()
        self.request = RequestFactory().post("/api/v1/cli/prompt/test/", data="{}", content_type="application/json")
        self.request.user = self.admin_user

    def view(self, **properties) -> ApiV1CliPromptApiView:
        """A view whose named properties return the given values."""
        defaults = {
            "data": {"prompt": "hello"},
            "url": "http://testserver/api/v1/cli/prompt/test/",
            "session_key": SESSION_KEY,
            "cache_key": f"test_prompt_view_handler_{self.hash_suffix}",
            "is_config": False,
            "uid": "test",
            "params": QueryDict(""),
            "account": self.account,
        }
        defaults.update(properties)
        stack = ExitStack()
        self.addCleanup(stack.close)
        for name, value in defaults.items():
            stack.enter_context(
                patch.object(ApiV1CliPromptApiView, name, new_callable=PropertyMock, return_value=value)
            )
        view = ApiV1CliPromptApiView()
        view.request = self.request
        view._chat_config = {}
        return view

    def handle(self, config_response, chat_response=None, **properties):
        """Run handler() with the prompt config and llmclient views returning the given responses."""
        view = self.view(**properties)
        with (
            patch(f"{MODULE}.PromptConfigView.as_view", return_value=MagicMock(return_value=config_response)),
            patch(f"{MODULE}.DefaultLLMClientApiView.as_view", return_value=MagicMock(return_value=chat_response)),
            patch.object(ApiV1CliPromptApiView, "chat_request_body_factory", return_value={}),
            patch.object(ApiV1CliPromptApiView, "chat_request_factory", return_value=self.request),
            patch(f"{MODULE}.waffle.switch_is_active", return_value=True),
        ):
            return view.handler(self.request, "test")

    def config(self, content: str = '{"data": {}}', status: int = 200) -> JsonResponse:
        response = JsonResponse({}, status=status)
        response.content = content
        return response

    def test_config_view_failures_raise(self):
        for config_response in (HttpResponse("not json"), self.config(status=500)):
            with self.subTest(config_response=config_response):
                with self.assertRaises(APIV1CLIChatViewError):
                    self.handle(config_response)

    def test_unreadable_config_content_raises(self):
        content_none = MagicMock(spec=JsonResponse, status_code=200, content=None)
        content_int = MagicMock(spec=JsonResponse, status_code=200, content=123)
        for config_response in (content_none, content_int, self.config(content="{not json")):
            with self.subTest(config_response=config_response):
                with self.assertRaises(APIV1CLIViewError):
                    self.handle(config_response)

    def test_chat_response_that_is_not_json_raises(self):
        with self.assertRaises(APIV1CLIChatViewError):
            self.handle(self.config(), chat_response=HttpResponse("not json"))

    def test_chat_response_without_a_body_is_an_error(self):
        for data in ({}, {"data": {"error": "provider failed"}}, {"data": {"something": "else"}}):
            with self.subTest(data=data):
                response = self.handle(self.config(), chat_response=JsonResponse(data))
                self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)

    def test_chat_response_body_is_unescaped(self):
        chat_response = JsonResponse({"data": {"body": json.dumps({"answer": 42})}})
        config = self.config(content=json.dumps({"data": {"session_key": SESSION_KEY}}))
        response = self.handle(config, chat_response=chat_response)
        self.assertEqual(response.status_code, HTTPStatus.OK)

    def initial(self, **properties):
        view = self.view(**properties)
        with (
            patch.object(CliBaseApiView, "initial"),
            patch.object(ApiV1CliPromptApiView, "validate"),
            patch(f"{MODULE}.waffle.switch_is_active", return_value=True),
        ):
            view.initial(self.request, name="test")
        return view

    def test_initial_needs_a_body_and_a_uid(self):
        with self.assertRaises(APIV1CLIChatViewError):
            self.initial(data=None)
        with self.assertRaises(APIV1CLIChatViewError):
            self.initial(uid=None)

    def test_initial_new_session_replaces_the_session_key(self):
        view = self.initial(params=QueryDict("new_session=true"), data=["not", "a", "dict"])
        self.assertIn("session_key", json.loads(self.request._body))
        self.assertNotEqual(view._session_key, SESSION_KEY)

    def test_validate_needs_a_prompt(self):
        view = self.view(prompt=None)
        with self.assertRaises(APIV1CLIChatViewError):
            view.validate()

    def test_post_for_an_unknown_llmclient_is_not_found(self):
        view = self.view()
        response = view.post(self.request, f"no_such_llmclient_{self.hash_suffix}")
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_post_handler_failure_is_an_internal_error(self):
        view = self.view()
        with (
            patch(f"{MODULE}.LLMClient.objects.filter") as llmclient_filter,
            patch.object(ApiV1CliPromptApiView, "handler", side_effect=RuntimeError("boom")),
        ):
            llmclient_filter.return_value.with_read_permission_for.return_value.exists.return_value = True
            response = view.post(self.request, "test")
        self.assertEqual(response.status_code, HTTPStatus.INTERNAL_SERVER_ERROR)
