"""
Test the Prompt dashboard views: the React list of LLMClients, its list, clone, delete and rename api, the LLMClient manifest page, and the sandbox, prompt workbench and config pages.

See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

import secrets
from http import HTTPStatus
from unittest.mock import MagicMock, patch
from urllib.parse import urlparse

from django.test import RequestFactory

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.caching import (
    invalidate_all_cached_llmclients_for_user_profile,
)
from smarter.apps.llmclient.models import LLMClient
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
        module = "smarter.apps.prompt.views.detailviews.prompt_workbench_view.smarter_settings"

        class Settings:
            """Smarter_settings, which is frozen, with log viewing in the browser enabled or not."""

            def __init__(self, enabled: bool):
                self.enable_dashboard_server_logs = enabled

            def __getattr__(self, name):
                return getattr(smarter_settings, name)

        with patch(module, Settings(True)):
            response = self.client.get(url, HTTP_HOST=PLATFORM_HOST)
        log_stream_url = response.context["smarter_chat"]["log_stream_url"]
        self.assertTrue(log_stream_url.endswith("/logs/api/stream/"), log_stream_url)
        self.assertIn(f'smarter-log-stream-url="{log_stream_url}"', response.content.decode())

        with patch(module, Settings(False)):
            response = self.client.get(url, HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(response.context["smarter_chat"]["log_stream_url"], "")

    def test_workbench_and_config_not_found(self):
        """Test that the workbench page and config api are a 404 for an unknown LLMClient."""
        unknown = LLMClient(id=999999999)
        response = self.client.get(self.url("chat_by_hashed_id", hashed_id=unknown.hashed_id), HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.client.post(self.url("config_by_hashed_id", hashed_id=unknown.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

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
        self.assertEqual(session, session)
        self.assertNotEqual(session, session_key)
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
