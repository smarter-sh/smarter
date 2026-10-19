"""
Test the Prompt dashboard views: the React list of LLMClients, its list, clone, delete and rename api, the LLMClient manifest page, and the sandbox, prompt workbench and config pages.

See :class:`smarter.lib.unittest.resource_views.ResourceViewsTestMixin`.
"""

import json
import secrets
from http import HTTPStatus
from unittest.mock import MagicMock, PropertyMock, call, patch
from urllib.parse import urlparse

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory, override_settings

from smarter.apps.account.tests.factories import admin_user_factory
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.llmclient.caching import (
    invalidate_all_cached_llmclients_for_user_profile,
)
from smarter.apps.llmclient.models import LLMClient, LLMClientAPIKey, LLMClientHelper
from smarter.apps.prompt.contract.const import (
    CHAT_CONTRACT_V2_CAPABILITY,
    PUBLIC_META_DATA_FIELDS,
    VERBOSE_PARAMETER,
)
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
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.logging.redis_log_handler import session_key_context
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

    def test_list_api_pending_filter(self):
        """Test that ?filter=pending lists only the LLMClients that aren't deployed, as the dashboard counts them."""
        deployed = self.throwaway("deployed")
        pending = self.throwaway("pending")
        LLMClient.objects.filter(pk=deployed.pk).update(deployed=True)
        LLMClient.objects.filter(pk=pending.pk).update(deployed=False)
        names = self.listed("owned", filter="pending", invalidate_cache="true", page_size=100)
        self.assertIn(pending.name, names)
        self.assertNotIn(deployed.name, names)
        self.assertIn(deployed.name, self.listed("owned", invalidate_cache="true", page_size=100))

        url = self.url("listview_api", ownership_filter="owned") + "?filter=pending&invalidate_cache=true"
        pagination = self.post(url)["pagination"]
        self.assertEqual((pagination["filter"], pagination["filters"]), ("pending", ["pending"]))

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

    def test_workbench_manifest_editor_url(self):
        """Test that the workbench passes the LLMClient's manifest editor, of its own origin, to Smarter Chat."""
        response = self.client.get(
            self.url("chat_by_hashed_id", hashed_id=self.resource.hashed_id), HTTP_HOST=PLATFORM_HOST
        )
        manifest_editor_url = response.context["smarter_chat"]["manifest_editor_url"]
        self.assertEqual(
            manifest_editor_url, self.url("manifest_editor_by_hashed_id", hashed_id=self.resource.hashed_id)
        )
        # a path, of the workbench's own origin, as Smarter Chat requires.
        self.assertTrue(manifest_editor_url.startswith("/"), manifest_editor_url)
        self.assertTrue(manifest_editor_url.endswith("/manifest/editor/"), manifest_editor_url)
        self.assertIn(f'smarter-manifest-editor-url="{manifest_editor_url}"', response.content.decode())

    def test_manifest_editor(self):
        """Test that the manifest editor page renders the editor alone, and may be framed by the console only."""
        response = self.client.get(self.url("manifest_editor_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        templates = [template.name for template in response.templates]
        self.assertIn("common/manifest_editor_frame.html", templates)
        self.assertIn("common/manifest_editor.html", templates)
        # without the web console's header and sidebar.
        self.assertNotIn("dashboard/base.html", templates)
        self.assertNotIn("dashboard/sidebar.html", templates)
        content = response.content.decode()
        self.assertIn('id="smarter-manifest-editor-root"', content)
        self.assertIn(self.resource.name, content)
        # Django denies every other page to frames.
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")

    def test_manifest_editor_not_found(self):
        """Test that the manifest editor page is a 404 for an unknown LLMClient."""
        unknown = LLMClient(id=999999999)
        response = self.client.get(self.url("manifest_editor_by_hashed_id", hashed_id=unknown.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_workbench_deployment_url(self):
        """Test that the workbench passes the LLMClient's deployment page, of its own origin, to Smarter Chat."""
        response = self.client.get(
            self.url("chat_by_hashed_id", hashed_id=self.resource.hashed_id), HTTP_HOST=PLATFORM_HOST
        )
        deployment_url = response.context["smarter_chat"]["deployment_url"]
        self.assertEqual(deployment_url, self.url("deployment_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(deployment_url, f"/workbench/llm-clients/{self.resource.hashed_id}/deployment/")
        self.assertIn(f'smarter-deployment-url="{deployment_url}"', response.content.decode())

    def test_deployment(self):
        """Test that the deployment page renders alone, whatever the endpoints page's switch, and may be framed."""
        LLMClient.objects.filter(pk=self.resource.pk).update(deployed=True)
        self.addCleanup(LLMClient.objects.filter(pk=self.resource.pk).update, deployed=False)
        with patch("smarter.apps.llmclient.views.endpoints.waffle.switch_is_active", return_value=False):
            response = self.client.get(self.url("deployment_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        templates = [template.name for template in response.templates]
        self.assertIn("llmclient/deployment_frame.html", templates)
        self.assertIn("llmclient/deployment.html", templates)
        self.assertNotIn("dashboard/base.html", templates)
        self.assertFalse(response.context["standalone"])
        self.assertTrue(response.context["deployed"])
        content = response.content.decode()
        self.assertIn("Where to go from here?", content)
        self.assertIn(self.resource.default_url.rstrip("/"), content)
        # the tab is in the workbench: no way back to it, and none of the endpoints page's own sections.
        self.assertNotIn("Back to the workbench", content)
        self.assertNotIn("waffle_switch enable_llmclient_endpoints_page off", content)
        self.assertIn("enable_llmclient_endpoints_page", content)
        self.assertEqual(response["X-Frame-Options"], "SAMEORIGIN")
        self.assertIn("no-cache", response["Cache-Control"])

    def test_deployment_of_an_llmclient_that_is_not_deployed(self):
        """Test that the deployment page tells how to deploy an LLMClient that isn't deployed."""
        LLMClient.objects.filter(pk=self.resource.pk).update(deployed=False)
        response = self.client.get(self.url("deployment_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        content = response.content.decode()
        self.assertIn("Not deployed yet", content)
        self.assertIn(f"smarter deploy llmclient {self.resource.name}", content)

    def test_deployment_not_found(self):
        """Test that the deployment page is a 404 for an unknown LLMClient, and for another account's."""
        unknown = LLMClient(id=999999999)
        response = self.client.get(self.url("deployment_by_hashed_id", hashed_id=unknown.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        response = self.client.get(self.url("deployment_by_hashed_id", hashed_id="not-a-hashed-id"))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

        other_admin_user, _, _ = admin_user_factory()
        other_admin_user.is_superuser = False
        other_admin_user.save()
        self.client.force_login(other_admin_user)
        response = self.client.get(self.url("deployment_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def deployment_post(self, **data):
        """POST the deployment page's api key form."""
        return self.client.post(self.url("deployment_by_hashed_id", hashed_id=self.resource.hashed_id), data)

    def api_key(self, name: str) -> SmarterAuthToken:
        """An api key of the admin user, deleted after the test."""
        api_key, _ = SmarterAuthToken.objects.create(
            user=self.admin_user, user_profile=self.user_profile, name=f"{name}_{secrets.token_hex(4)}"
        )
        self.addCleanup(SmarterAuthToken.objects.filter(pk=api_key.pk).delete)
        return api_key

    def detach_api_keys(self):
        self.addCleanup(LLMClientAPIKey.detach, self.resource)

    def test_deployment_lists_attaches_and_detaches_api_keys(self):
        """Test that the deployment page lists the account's api keys, attaches one in place of another, and detaches it."""
        self.detach_api_keys()
        first, second = self.api_key("first"), self.api_key("second")
        response = self.client.get(self.url("deployment_by_hashed_id", hashed_id=self.resource.hashed_id))
        content = response.content.decode()
        self.assertIn(first.name, content)
        self.assertIn(second.name, content)
        self.assertIn("No api key is attached: the url is public.", content)
        self.assertIn("csrfmiddlewaretoken", content)

        response = self.deployment_post(action="attach", key_id=str(first.key_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIn(f"{first.name} is attached", response.content.decode())
        self.assertTrue(LLMClient.objects.get(pk=self.resource.pk).is_authentication_required)
        self.assertEqual(response.context["attached_api_key"]["name"], first.name)
        self.assertTrue(response.context["authenticated"])

        # one api key: attaching another detaches the first.
        self.deployment_post(action="attach", key_id=str(second.key_id))
        self.assertEqual(
            list(LLMClientAPIKey.objects.filter(llmclient=self.resource).values_list("api_key", flat=True)),
            [second.pk],
        )

        response = self.deployment_post(action="detach")
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertFalse(LLMClientAPIKey.objects.filter(llmclient=self.resource).exists())
        self.assertFalse(LLMClient.objects.get(pk=self.resource.pk).is_authentication_required)

    def test_deployment_creates_an_api_key(self):
        """Test that the deployment page creates an api key, shows its secret once, and attaches it."""
        self.detach_api_keys()
        name = f"test_deployment_{secrets.token_hex(4)}"
        self.addCleanup(SmarterAuthToken.objects.filter(name=name).delete)
        response = self.deployment_post(action="create", name=name, description="the chat", attach="1")
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        api_key = SmarterAuthToken.objects.get(name=name, user=self.admin_user)
        self.assertEqual(api_key.description, "the chat")
        secret = response.context["new_api_key"]["secret"]
        self.assertIn(secret, response.content.decode())
        self.assertTrue(LLMClientAPIKey.objects.filter(llmclient=self.resource, api_key=api_key).exists())
        # the secret is the key: it authenticates.
        self.assertTrue(secret.startswith(api_key.token_key))
        # shown once: not on the next page.
        response = self.client.get(self.url("deployment_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertNotIn(secret, response.content.decode())

        # a second key of the same name is refused, and so is an invalid name.
        self.assertEqual(self.deployment_post(action="create", name=name).status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(self.deployment_post(action="create", name="").status_code, HTTPStatus.BAD_REQUEST)

    def test_deployment_creates_an_api_key_without_attaching_it(self):
        """Test that the deployment page creates an api key without attaching it, when asked to."""
        self.detach_api_keys()
        name = f"test_deployment_{secrets.token_hex(4)}"
        self.addCleanup(SmarterAuthToken.objects.filter(name=name).delete)
        response = self.deployment_post(action="create", name=name)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertFalse(LLMClientAPIKey.objects.filter(llmclient=self.resource).exists())

    def test_deployment_api_key_errors(self):
        """Test that the deployment page refuses an unknown action and an unknown api key."""
        self.assertEqual(self.deployment_post(action="nope").status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(self.deployment_post(action="attach").status_code, HTTPStatus.BAD_REQUEST)
        response = self.deployment_post(action="attach", key_id="00000000-0000-0000-0000-000000000000")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        unknown = LLMClient(id=999999999)
        response = self.client.post(
            self.url("deployment_by_hashed_id", hashed_id=unknown.hashed_id), {"action": "detach"}
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_deployment_api_keys_of_a_user_who_is_not_an_admin(self):
        """Test that a user who isn't an account admin sees the LLMClient's api key, but can't change it or create one."""
        self.detach_api_keys()
        api_key = self.api_key("admins")
        LLMClientAPIKey.attach(self.resource, api_key)
        self.client.force_login(self.non_admin_user)
        response = self.client.get(self.url("deployment_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertFalse(response.context["can_manage_api_keys"])
        self.assertFalse(response.context["can_create_api_keys"])
        content = response.content.decode()
        self.assertIn("Only an account admin can create api keys.", content)
        self.assertNotIn('value="detach"', content)

        self.assertEqual(self.deployment_post(action="detach").status_code, HTTPStatus.FORBIDDEN)
        self.assertEqual(self.deployment_post(action="create", name="not_allowed").status_code, HTTPStatus.FORBIDDEN)
        self.assertTrue(LLMClientAPIKey.objects.filter(llmclient=self.resource, api_key=api_key).exists())
        self.assertFalse(SmarterAuthToken.objects.filter(name="not_allowed").exists())

    def test_detail_page_may_not_be_framed(self):
        """Test that the manifest detail page, unlike the manifest editor page, may not be framed."""
        response = self.client.get(self.url("manifest_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertEqual(response["X-Frame-Options"], "DENY")
        self.assertIn("dashboard/base.html", [template.name for template in response.templates])

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

    def test_config_is_lean_by_default(self):
        """Test that the complete configuration leaves out its diagnostic parts unless the client asks for them."""
        response = self.client.post(self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id))
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        data = PromptChatApiConfigResponse.model_validate(response.json()).data
        payload = response.json()["data"]
        self.assertEqual(set(payload["history"]), {"chat_history"})
        self.assertLessEqual(set(payload["meta_data"]), set(PUBLIC_META_DATA_FIELDS))
        self.assertIn("is_authentication_required", payload["meta_data"])
        self.assertEqual(data.plugins.plugins, [])
        self.assertEqual(data.plugins.meta_data.plugins_returned, 0)
        self.assertIsInstance(data.plugins.meta_data.total_plugins, int)
        self.assertEqual(data.extensions.extensions if data.extensions else [], [])
        # the complete LLMClient, e.g. its owner's profile, isn't diagnostic.
        self.assertIn("user_profile", payload["llmclient"])

    def test_config_verbose(self):
        """Test that ?verbose=true adds the tool calls, the complete meta data, and the plugin and extension lists."""
        url = self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id)
        for value in ("true", "1", "True"):
            with self.subTest(value=value):
                response = self.client.post(f"{url}?{VERBOSE_PARAMETER}={value}")
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
                data = PromptChatApiConfigResponse.model_validate(response.json()).data
                payload = response.json()["data"]
                self.assertEqual(set(payload["history"]), {"chat_history", "prompt_tool_call_history"})
                self.assertIn("llmclient", payload["meta_data"])
                self.assertIn("plugins", payload["plugins"])
                self.assertEqual(
                    data.plugins.meta_data.plugins_returned, min(data.plugins.meta_data.total_plugins or 0, 10)
                )
        response = self.client.post(f"{url}?{VERBOSE_PARAMETER}=false")
        self.assertEqual(set(response.json()["data"]["history"]), {"chat_history"})

    def test_config_tags_its_logs_with_the_session_key(self):
        """Test that the config api tags the rest of its request's logs with the chat's session key, e.g. a new one."""
        module = "smarter.apps.prompt.views.detailviews.prompt_config_view"
        url = self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id)
        with (
            patch(f"{module}.waffle.switch_is_active", return_value=True),
            patch(f"{module}.session_key_context") as session_key_context,
        ):
            response = self.client.post(url, HTTP_X_SMARTER_CAPABILITIES=CHAT_CONTRACT_V2_CAPABILITY)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        session_key = PromptChatApiConfigResponse.model_validate(response.json()).data.session_key
        # dispatch() scopes the context to the request, then the session key is set in it.
        scope = call(session_key_context.get.return_value)
        self.assertEqual(session_key_context.set.call_args_list, [scope, call(session_key)])
        session_key_context.reset.assert_called_once_with(session_key_context.set.return_value)

        # while server logs are off, the session key isn't set.
        with (
            patch(f"{module}.waffle.switch_is_active", return_value=False),
            patch(f"{module}.session_key_context") as session_key_context,
        ):
            self.client.post(url)
        self.assertEqual(session_key_context.set.call_args_list, [call(session_key_context.get.return_value)])

    def test_config_restores_the_log_context(self):
        """Test that the config api's session key doesn't outlive its request, even without the log context middleware."""
        module = "smarter.apps.prompt.views.detailviews.prompt_config_view"
        request = RequestFactory().post(self.url("config_by_hashed_id", hashed_id=self.resource.hashed_id))
        request.user = self.admin_user
        self.assertIsNone(session_key_context.get())
        with patch(f"{module}.waffle.switch_is_active", return_value=True):
            response = PromptConfigView.as_view()(request, hashed_id=self.resource.hashed_id)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIsNone(session_key_context.get())

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
        self.assertIsInstance(data["llmclient"]["total_tools"], int)
        content = response.content.decode()
        self.assertNotIn(self.admin_user.email, content)
        self.assertNotIn(self.admin_user.username, content)

    def test_public_config_ignores_verbose(self):
        """Test that a deployed LLMClient's own host returns its public configuration, even with ?verbose=true."""
        request = RequestFactory().post(
            f"/config/?{VERBOSE_PARAMETER}=true", data={}, content_type="application/json", HTTP_HOST=self.host
        )
        request.user = self.admin_user
        with (
            override_settings(ALLOWED_HOSTS=["*"]),
            patch(
                "smarter.apps.prompt.views.detailviews.prompt_config_view.get_cached_llmclient_by_request",
                return_value=self.llmclient,
            ),
            patch.object(LLMClientHelper, "to_json") as to_json,
        ):
            response = PromptConfigView.as_view()(request)
        self.addCleanup(Prompt.objects.filter(llmclient=self.llmclient).delete)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        data = json.loads(response.content)["data"]
        self.assertEqual(set(data["history"]), {"chat_history"})
        self.assertLessEqual(set(data["meta_data"]), set(PUBLIC_META_DATA_FIELDS))
        # the complete meta data is never built for the public configuration.
        to_json.assert_not_called()

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
