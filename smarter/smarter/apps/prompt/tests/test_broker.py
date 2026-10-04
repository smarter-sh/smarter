"""
Test the Prompt manifest broker, :mod:`smarter.apps.prompt.manifest.brokers.prompt`, through the.

api/v1/cli/ commands. A Prompt is a chat session, a read-only resource that apply refuses.
"""

import secrets
from http import HTTPStatus

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.models import Prompt
from smarter.lib.manifest.enum import SAMKeys
from smarter.lib.unittest.cli_brokers import (
    NOT_FOUND,
    NOT_IMPLEMENTED,
    CliBrokerTestMixin,
)

REFUSED = (HTTPStatus.BAD_REQUEST, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND, HTTPStatus.METHOD_NOT_ALLOWED)


class TestPromptBroker(CliBrokerTestMixin, ApiV1TestBase):
    """Test the Prompt broker."""

    kind = SAMKinds.PROMPT.value
    model = Prompt
    name_prefix = "test_prompt_broker"

    def test_example_manifest(self):
        manifest = self.example_manifest()
        self.assertEqual(manifest["metadata"]["version"], "1.0.0")

    def test_get(self):
        response = self.cli("get")
        self.assertIn("count", response["data"]["metadata"])
        self.cli("get", session_key="no-such-session")

    def test_apply_describe_delete(self):
        """Test that apply is refused, because a Prompt is read-only."""
        manifest = self.prepare_manifest(self.example_manifest())
        # the example manifest is loadable, so apply reaches the broker, which refuses it as read-only.
        self.cli("apply", data=manifest, with_kind=False, status=(HTTPStatus.METHOD_NOT_ALLOWED,))

    def test_describe(self):
        """Test that describe returns the Prompt of the name, with its chat session in the spec."""
        llmclient = LLMClient.objects.create(name=f"{self.name}_llmclient", user_profile=self.user_profile)
        self.addCleanup(llmclient.delete)
        prompt = Prompt.objects.create(
            name=self.name,
            session_key=secrets.token_hex(32),
            llmclient=llmclient,
            user_profile=self.user_profile,
            ip_address="192.168.1.1",
            user_agent="Mozilla/5.0",
            url="https://www.example.com/",
        )
        response = self.cli("describe", name=self.name)
        spec = response["data"][SAMKeys.SPEC.value]
        self.assertEqual(spec["sessionKey"], prompt.session_key)
        self.assertEqual(spec["llmclient"], llmclient.name)
        self.assertEqual(spec["url"], prompt.url)

    def test_deploy_undeploy_logs(self):
        for command in ("deploy", "undeploy", "logs"):
            with self.subTest(command=command):
                self.cli(command, status=NOT_IMPLEMENTED + REFUSED + NOT_FOUND)
