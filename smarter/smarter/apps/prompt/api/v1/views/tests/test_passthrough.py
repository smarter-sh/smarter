# pylint: disable=W0613,W0718
"""Test prompt API chat passthrough view"""

import logging
import os
from typing import Any, cast

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as smarter_apps_api_namespace
from smarter.apps.api.v1.const import namespace as smarter_apps_api_v1_namespace
from smarter.apps.prompt.api.v1.urls import PromptAPINamespace
from smarter.apps.prompt.const import namespace as smarter_apps_prompt_namespace
from smarter.common.helpers.console_helpers import formatted_json

# api:v1:prompt:passthrough
namespace = ":".join(
    [
        smarter_apps_api_namespace,
        smarter_apps_api_v1_namespace,
        smarter_apps_prompt_namespace,
        PromptAPINamespace.passthrough,
    ]
)
HERE = os.path.abspath(os.path.dirname(__file__))

logger = logging.getLogger(__name__)


class TestPassthroughView(TestAccountMixin):
    """Test prompt API chat passthrough view."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.prompt_data: dict[str, Any] = cast(
            dict[str, Any], self.get_readonly_json_file(os.path.join(HERE, "data", "openai_passthrough_prompt.json"))
        )
        logger.debug("Loaded prompt data for testing passthrough view: %s", formatted_json(self.prompt_data))

        # /api/v1/prompts/passthrough/openai/
        self.url = reverse(namespace, args=["openai"])
        logger.debug("Set up TestPassthroughView with namespace: %s  URL: %s", namespace, self.url)

    def test_passthrough_view(self):
        """Test that we can create a chat completion using the passthrough view."""
        response = self.client.post(self.url, data=self.prompt_data, content_type="application/json")
        self.assertEqual(response.status_code, 200)
        logger.debug(
            "Received response with status code: %s and content: %s",
            response.status_code,
            formatted_json(response.json()),
        )

    def test_illegal_key(self):
        """Test that we get a 400 response if we include an illegal key in the request."""
        self.prompt_data["illegal_key"] = "illegal_value"
        response = self.client.post(self.url, data=self.prompt_data, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        logger.debug(
            "Received response with status code: %s and content: %s",
            response.status_code,
            formatted_json(response.json()),
        )
