"""Test :mod:`smarter.apps.prompt.contract.history`, and the prompt history's real responses against the OpenAPI document."""

import json
import secrets
from http import HTTPStatus
from unittest.mock import patch

from pydantic import ValidationError
from rest_framework.test import APIClient

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.llmtool.models import PluginMeta
from smarter.apps.prompt.api.v1.serializers import (
    PromptSerializer,
    PromptToolCallSerializer,
)
from smarter.apps.prompt.contract.history import (
    PromptHistoryApiPluginUsage,
    PromptHistoryApiSession,
    PromptHistoryApiToolCall,
)
from smarter.apps.prompt.models import Prompt, PromptPluginUsage, PromptToolCall


class TestPromptHistoryContract(OpenApiResponseMixin, TestAccountMixin):
    """Test the prompt history's models against the serializers, and the views' responses against the document."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        patcher = patch("smarter.apps.prompt.receivers.create_prompt_history")
        patcher.start()
        cls.addClassCleanup(patcher.stop)
        cls.llmclient = LLMClient.objects.create(
            name=f"test_prompt_history_{cls.hash_suffix}", user_profile=cls.user_profile, deployed=False
        )
        cls.plugin = PluginMeta.objects.create(
            name=f"test_prompt_history_{cls.hash_suffix}", user_profile=cls.user_profile, plugin_class="static"
        )
        cls.prompt = cls.session(cls.user_profile)
        cls.tool_call = PromptToolCall.objects.create(
            prompt=cls.prompt,
            plugin=cls.plugin,
            function_name="calculator",
            function_args="{'expression': '17 * 23'}",
            request=[{"role": "user", "content": "17 * 23?"}],
            response={"result": 391},
        )
        cls.plugin_usage = PromptPluginUsage.objects.create(prompt=cls.prompt, plugin=cls.plugin, input_text="17 * 23?")
        # another account's user, whose session nobody else may read.
        cls.stranger, cls.stranger_account, cls.stranger_profile = mortal_user_factory()
        cls.stranger_prompt = cls.session(cls.stranger_profile)

    @classmethod
    def session(cls, user_profile) -> Prompt:
        return Prompt.objects.create(
            session_key=secrets.token_hex(32),
            user_profile=user_profile,
            llmclient=cls.llmclient,
            ip_address="192.0.2.1",
            user_agent="unit test",
            url="https://www.example.com",
        )

    @classmethod
    def tearDownClass(cls):
        Prompt.objects.filter(pk__in=[cls.prompt.pk, cls.stranger_prompt.pk]).delete()
        cls.plugin.delete()
        cls.llmclient.delete()
        UserProfile.objects.filter(pk=cls.stranger_profile.pk).delete()
        User.objects.filter(pk=cls.stranger.pk).delete()
        Account.objects.filter(pk=cls.stranger_account.pk).delete()
        super().tearDownClass()

    def serialized(self, serializer_class, row) -> dict:
        return json.loads(json.dumps(serializer_class(row).data, default=str))

    def test_models_are_the_serializers_output(self):
        self.assertEqual(
            PromptHistoryApiSession.from_model(self.prompt).model_dump(mode="json"),
            self.serialized(PromptSerializer, self.prompt),
        )
        self.assertEqual(
            PromptHistoryApiToolCall.from_model(self.tool_call).model_dump(mode="json"),
            self.serialized(PromptToolCallSerializer, self.tool_call),
        )

    def test_plugin_usage(self):
        usage = PromptHistoryApiPluginUsage.from_model(self.plugin_usage, self.admin_user)
        self.assertEqual(usage.prompt.id, self.prompt.pk)
        self.assertEqual(usage.plugin.name, self.plugin.name)
        self.assertEqual(usage.model_dump(mode="json")["plugin"]["pluginClass"], "static")

    def test_extra_fields_are_forbidden(self):
        data = PromptHistoryApiSession.from_model(self.prompt).model_dump(mode="json")
        with self.assertRaises(ValidationError):
            PromptHistoryApiSession.model_validate({**data, "tags": []})

    def test_responses(self):
        client = APIClient()
        client.force_login(self.non_admin_user)
        # the session's owner is the account's admin. A user of the account who is not its admin may not read it.
        self.assertEqual(client.get("/api/v1/prompts/history/prompt/").json(), [])
        client.force_login(self.admin_user)
        for template, path in {
            "/prompts/history/prompt/": "/prompts/history/prompt/",
            "/prompts/history/prompt/{id}/": f"/prompts/history/prompt/{self.prompt.pk}/",
            "/prompts/history/tool-calls/": "/prompts/history/tool-calls/",
            "/prompts/history/tool-calls/{id}/": f"/prompts/history/tool-calls/{self.tool_call.pk}/",
            "/prompts/history/plugin-usage/": "/prompts/history/plugin-usage/",
            "/prompts/history/plugin-usage/{id}/": f"/prompts/history/plugin-usage/{self.plugin_usage.pk}/",
        }.items():
            with self.subTest(path=template):
                response = client.get(f"/api/v1{path}")
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content)
                self.assertValidResponse(template, "get", response.json())

    def test_other_accounts_sessions_are_private(self):
        client = APIClient()
        client.force_login(self.stranger)
        sessions = client.get("/api/v1/prompts/history/prompt/").json()
        self.assertEqual([session["id"] for session in sessions], [self.stranger_prompt.pk])
        self.assertEqual(client.get("/api/v1/prompts/history/tool-calls/").json(), [])
        self.assertEqual(client.get("/api/v1/prompts/history/plugin-usage/").json(), [])
        for path in (
            f"/prompts/history/prompt/{self.prompt.pk}/",
            f"/prompts/history/tool-calls/{self.tool_call.pk}/",
            f"/prompts/history/plugin-usage/{self.plugin_usage.pk}/",
        ):
            with self.subTest(path=path):
                response = client.get(f"/api/v1{path}")
                self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
                self.assertValidResponse("/prompts/history/prompt/{id}/", "get", response.json(), HTTPStatus.NOT_FOUND)
