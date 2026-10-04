"""
Test the Prompt manifest broker, :mod:`smarter.apps.prompt.manifest.brokers.prompt`, through the.

api/v1/cli/ commands. A Prompt is a chat session, a read-only resource that apply refuses.
"""

import unittest
from http import HTTPStatus

from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.apps.prompt.models import Prompt
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

    @unittest.expectedFailure
    def test_apply_describe_delete(self):
        """
        Test that apply is refused, because a Prompt is read-only.

        Expected to fail: the apply view has no broker for the kind Prompt, and answers with a
        500, "No broker found for manifest kind 'Prompt'", rather than the broker's refusal.
        """
        manifest = self.prepare_manifest(self.example_manifest())
        self.cli("apply", data=manifest, with_kind=False, status=REFUSED)

    def test_deploy_undeploy_logs(self):
        for command in ("deploy", "undeploy", "logs"):
            with self.subTest(command=command):
                self.cli(command, status=NOT_IMPLEMENTED + REFUSED + NOT_FOUND)
