"""
Test the Prompt dashboard views: the React list of LLMClients, its list, clone, delete and rename api, the LLMClient manifest page, and the sandbox, prompt workbench and config pages.

See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

import json
import secrets
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, patch
from urllib.parse import urlparse

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.caching import (
    invalidate_all_cached_llmclients_for_user_profile,
)
from smarter.apps.llmclient.models import LLMClient, LLMClientHelper
from smarter.apps.prompt.contract.const import CHAT_CONTRACT_V2_CAPABILITY
from smarter.apps.prompt.contract.models import (
    PromptChatApiConfigResponse,
    PromptChatApiConfigResponseV1,
    PromptChatApiErrorResponse,
)
from smarter.apps.prompt.models import Prompt
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.apps.prompt.views.detailviews.prompt_config_view import PromptConfigView
from smarter.apps.prompt.views.detailviews.prompt_workbench_view import (
    SmarterChatappViewError,
    SmarterPromptSession,
)
from smarter.common.conf import smarter_settings
from smarter.lib.unittest.resource_views import ResourceViewsTestMixin

PLATFORM_HOST = urlparse(smarter_settings.environment_platform_url).netloc


class TestPromptViews(ResourceViewsTestMixin, TestAccountMixin):
    """Test the Prompt dashboard views, whose resource is an LLMClient."""

    model = LLMClient
    reverse_names = PromptReverseNames
    id_kwarg = "llmclient_id"
    invalidate_cache = staticmethod(invalidate_all_cached_llmclients_for_user_profile)
    resource_name_prefix = "test_prompt_views"
    detail_view_name = "manifest_by_hashed_id"

    @classmethod
    def create_resource(cls, name: str) -> LLMClient:
        return LLMClient.objects.create(name=name, user_profile=cls.user_profile)

    def test_detail(self):
        super().test_detail()

    def test_config_other_account(self):
        """Test that another account's admin cannot read the LLMClient's configuration."""
        other_admin_user, _, _ = admin_user_factory()
        # admin_user_factory() users are superusers, who may read every account's resources.
        other_admin_user.is_superuser = False
        other_admin_user.save()
        self.client.force_login(other_admin_user)
        response = self.client.post(self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertIn(response.status_code, (HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND), response.content[:300])

    def test_sandbox(self):
        """Test that the sandbox url, which only provides the base url of the workbench pages, is a 404."""
        response = self.client.get(self.url("sandbox_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_config(self):
        """Test that the config api returns the LLMClient's configuration to a POST, and refuses a GET."""
        url = self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id)
        response = self.client.post(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertEqual(self.client.get(url).status_code, HTTPStatus.METHOD_NOT_ALLOWED)

    def test_workbench(self):
        """Test that the prompt workbench page renders Smarter Chat's root element, configured for the LLMClient."""
        response = self.client.get(
            self.url("chat_by_hashed_id", hashed_id=self.resource.hashed_id), HTTP_HOST=PLATFORM_HOST
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIn("react/smarter-chat.html", [template.name for template in response.templates])
        smarter_chat = response.context["smarter_chat"]
        self.assertEqual(smarter_chat["root_id"], "smarter-chat-root")
        self.assertEqual(smarter_chat["llmclient_api_url"], self.resource.sandbox_url)
        content = response.content.decode()
        self.assertIn('id="smarter-chat-root"', content)
        self.assertIn(f'smarter-llmclient-api-url="{self.resource.sandbox_url}"', content)
        self.assertIn(f'smarter-request-id="{smarter_chat["smarter_request_id"]}"', content)
        # the app is built into Django's static files, not loaded from a CDN.
        self.assertNotIn("app-loader.js", content)

    def test_workbench_log_stream_url(self):
        """Test that the workbench passes the user's server log stream to Smarter Chat, when it is enabled."""
        url = self.url("chat_by_hashed_id", hashed_id=self.resource.hashed_id)
        enabled = "smarter.apps.dashboard.views.terminal_emulator.enabled.server_logs_enabled"

        with patch(enabled, return_value=True):
            response = self.client.get(url, HTTP_HOST=PLATFORM_HOST)
        log_stream_url = response.context["smarter_chat"]["log_stream_url"]
        self.assertTrue(log_stream_url.endswith("/logs/api/stream/"), log_stream_url)
        self.assertIn(f'smarter-log-stream-url="{log_stream_url}"', response.content.decode())

        # without a log stream, Smarter Chat has no "Server Logs" tab.
        with patch(enabled, return_value=False):
            response = self.client.get(url, HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(response.context["smarter_chat"]["log_stream_url"], "")
        self.assertIn('smarter-log-stream-url=""', response.content.decode())

    def test_workbench_and_config_not_found(self):
        """Test that the workbench page and config api are a 404 for an unknown LLMClient."""
        unknown = LLMClient(id=999999999)
        response = self.client.get(self.url("chat_by_hashed_id", hashed_id=unknown.hashed_id), HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.client.post(self.url("config_by_hashed_id", hashed_id=unknown.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_config_v1_matches_the_contract(self):
        """Test that Smarter Chat up to 0.7, which lists no contract capability, receives version 1, complete for its owner."""
        response = self.client.post(
            self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id),
            HTTP_X_SMARTER_CLIENT="@smarter.sh/ui-chat",
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        config = PromptChatApiConfigResponseV1.model_validate(response.json())
        self.assertNotIn("contract", response.json()["data"])
        # a workbench url keeps the platform's prompt api url.
        self.assertEqual(config.data.chatbot.url_chatbot, self.resource.url_llmclient)
        # the complete configuration includes e.g. the owner's profile.
        self.assertIn("user_profile", response.json()["data"]["chatbot"])

    def test_config_v2_matches_the_contract(self):
        """Test that a client that asks for version 2 of the contract receives it, without legacy keys."""
        response = self.client.post(
            self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id),
            HTTP_X_SMARTER_CAPABILITIES=CHAT_CONTRACT_V2_CAPABILITY,
        )
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        config = PromptChatApiConfigResponse.model_validate(response.json())
        self.assertEqual(config.data.contract, 2)
        self.assertEqual(config.data.llmclient.url_llmclient, self.resource.url_llmclient)
        content = response.content.decode()
        self.assertNotIn('"chatbot', content)
        self.assertNotIn("url_chatbot", content)

    def test_config_v2_is_the_default(self):
        """Test that a client that asks for no version of the contract receives version 2."""
        response = self.client.post(self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertEqual(PromptChatApiConfigResponse.model_validate(response.json()).data.contract, 2)

    def test_config_errors_share_one_envelope(self):
        """Test that a config api error is the contract's error envelope, without a stack trace."""
        unknown = LLMClient(id=999999999)
        response = self.client.post(self.url("config_by_hashed_id", hashed_id=unknown.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        error = PromptChatApiErrorResponse.model_validate(response.json()).error
        self.assertEqual(error.errorClass, "PromptChatApiErrorNotFound")
        self.assertEqual(error.description, "LLMClient not found.")
        self.assertNotIn("stacktrace", response.json()["error"])

    def test_config_is_csrf_exempt(self):
        """Test that the config api, which only reads, accepts a POST without a CSRF token."""
        self.assertTrue(getattr(PromptConfigView.as_view(), "csrf_exempt", False))

    def test_config_get_when_allowed(self):
        """Test that the config api answers a GET when the ALLOW_API_GET switch is active."""
        url = self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id)
        with patch(
            "smarter.apps.prompt.views.detailviews.prompt_config_view.waffle.switch_is_active", return_value=True
        ):
            response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])


class TestPromptSessionAndConfigView(TestAccountMixin):
    """Test SmarterPromptSession, and the PromptConfigView members that the config api doesn't reach."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_prompt_session_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        self.request = RequestFactory().get("/workbench/")
        self.request.user = self.admin_user

    def test_prompt_session(self):
        """Test that a session is established for a session key and LLMClient, and identified by its key."""
        session_key = secrets.token_hex(32)
        self.addCleanup(Prompt.objects.filter(session_key=session_key).delete)
        session = SmarterPromptSession(self.request, session_key, llmclient=self.llmclient)
        self.assertEqual(session.session_key, session_key)
        self.assertEqual(session.llmclient, self.llmclient)
        self.assertIsNotNone(session.chat_helper)
        self.assertIs(session.prompt, session.chat_helper.prompt)
        self.assertIn(session_key, str(session))
        self.assertEqual(repr(session), str(session))
        self.assertTrue(str(session).startswith(f"SmarterPromptSession[{id(session)}]"))
        self.assertEqual(session, session)
        self.assertNotEqual(session, session_key)
        self.assertIs(session.__eq__(session_key), NotImplemented)
        self.assertEqual(hash(session), hash(session_key))
        self.assertEqual(len({session, session}), 1)
        self.assertIn("SmarterPromptSession", session.formatted_class_name)
        self.assertEqual(
            session.clean_url("https://example.com/workbench/config/?a=1"), "https://example.com/workbench"
        )
        self.assertEqual(SmarterChatappViewError("x").get_formatted_err_message, "Smarter Chatapp error")

    def test_config_view_members(self):
        """Test the config view's url cleaning, llmclient_helper setter, and config() without a session."""
        view = PromptConfigView()
        self.assertEqual(view.clean_url("https://example.com/workbench/config/?a=1"), "https://example.com/workbench")
        self.assertEqual(view.clean_url("https://example.com/workbench/"), "https://example.com/workbench/")

        view.llmclient_helper = None  # type: ignore[assignment]
        self.assertIsNone(view.llmclient)

        # the helper's identity is None, because a view's user profile, once set, is immutable.
        helper = MagicMock(llmclient=self.llmclient, account=None, user=None, user_profile=None)
        view.llmclient_helper = helper
        self.assertEqual(view.llmclient, self.llmclient)
        self.assertEqual(str(view), str(self.llmclient))

        view.session = None
        self.assertEqual(view.config(), {})


class TestPromptConfigViewForDeployedHosts(TestAccountMixin):
    """Test the config api as a deployed LLMClient's own host serves it, to pages that embed Smarter Chat."""

    def setUp(self):
        super().setUp()
        self.llmclient = LLMClient.objects.create(
            name=f"test_public_config_{self.hash_suffix}", user_profile=self.user_profile
        )
        self.addCleanup(LLMClient.objects.filter(pk=self.llmclient.pk).delete)
        # update(), rather than save(), whose signals would deploy it.
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=True)
        self.llmclient.refresh_from_db()
        self.host = f"public-config-{self.hash_suffix}.{self.account.account_number}.api.example.com"

    def post(self, user=None, **headers):
        """POST /config/ to the LLMClient's host, anonymously by default."""
        request = RequestFactory().post(
            "/config/", data={}, content_type="application/json", HTTP_HOST=self.host, **headers
        )
        request.user = user or AnonymousUser()
        with (
            override_settings(ALLOWED_HOSTS=["*"]),
            patch(
                "smarter.apps.prompt.views.detailviews.prompt_config_view.get_cached_llmclient_by_request",
                return_value=self.llmclient,
            ),
        ):
            response = PromptConfigView.as_view()(request)
        self.addCleanup(Prompt.objects.filter(llmclient=self.llmclient).delete)
        return response

    def test_public_config_for_an_anonymous_client(self):
        """Test that a deployed LLMClient without api keys serves its public configuration to anyone."""
        response = self.post()
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        payload = json.loads(response.content)
        PromptChatApiConfigResponse.model_validate(payload)
        data = payload["data"]
        self.assertEqual(data["contract"], 2)
        self.assertNotIn("user_profile", data["llmclient"])
        self.assertEqual(set(data["history"]), {"chat_history"})
        self.assertEqual(data["plugins"]["plugins"], [])
        content = response.content.decode()
        self.assertNotIn(self.admin_user.email, content)
        self.assertNotIn(self.admin_user.username, content)

    def test_public_config_for_an_authenticated_client(self):
        """Test that an api key's user, too, receives only the public configuration from the host."""
        data = json.loads(self.post(user=self.non_admin_user).content)["data"]
        self.assertNotIn("user_profile", data["llmclient"])

    def test_public_config_v1(self):
        response = self.post(HTTP_X_SMARTER_CLIENT="@smarter.sh/ui-chat")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        PromptChatApiConfigResponseV1.model_validate(json.loads(response.content))
        data = json.loads(response.content)["data"]
        self.assertNotIn("user_profile", data["chatbot"])

    def test_prompt_url_is_on_the_same_host(self):
        """Test that the configuration sends the page's prompts to the host that served it."""
        data = json.loads(self.post().content)["data"]
        url = urlparse(data["llmclient"]["url_llmclient"])
        self.assertEqual(url.netloc, self.host)
        self.assertEqual(url.path, "/prompt/")

    def test_undeployed_llmclient_is_not_found(self):
        LLMClient.objects.filter(pk=self.llmclient.pk).update(deployed=False)
        self.llmclient.refresh_from_db()
        response = self.post()
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:500])
        error = PromptChatApiErrorResponse.model_validate(json.loads(response.content)).error
        self.assertEqual(error.errorClass, "PromptChatApiErrorNotFound")

    def test_llmclient_with_an_api_key_requires_authentication(self):
        with patch.object(LLMClientHelper, "is_authentication_required", new_callable=PropertyMock, return_value=True):
            response = self.post()
            self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN, response.content[:500])
            error = PromptChatApiErrorResponse.model_validate(json.loads(response.content)).error
            self.assertEqual(error.errorClass, "PromptChatApiErrorForbidden")
            # an api key's user may use it.
            self.assertEqual(self.post(user=self.non_admin_user).status_code, HTTPStatus.OK)

    def test_anonymous_client_of_a_workbench_url_is_not_found(self):
        """Test that a url with an id, which requires a user who may read the LLMClient, is a 404 to anonymous clients."""
        request = RequestFactory().post(f"/workbench/llm-clients/{self.llmclient.hashed_id}/config/")
        request.user = AnonymousUser()
        response = PromptConfigView.as_view()(request, hashed_id=self.llmclient.hashed_id)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_unresolved_host_is_not_found(self):
        """Test that a host that resolves to no LLMClient is the contract's 404, not a server error."""
        request = RequestFactory().post("/config/", data={}, content_type="application/json", HTTP_HOST=self.host)
        request.user = AnonymousUser()
        with (
            override_settings(ALLOWED_HOSTS=["*"]),
            patch(
                "smarter.apps.prompt.views.detailviews.prompt_config_view.get_cached_llmclient_by_request",
                return_value=None,
            ),
            patch("smarter.apps.prompt.views.detailviews.prompt_config_view.LLMClientHelper") as helper,
        ):
            helper.return_value.llmclient = None
            response = PromptConfigView.as_view()(request)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND, response.content[:300])
