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
from smarter.apps.provider.services.text_completion.googleai.const import (
    PROVIDER_NAME as GOOGLEAI_PROVIDER_NAME,
)
from smarter.apps.provider.services.text_completion.metaai.const import (
    PROVIDER_NAME as METAAI_PROVIDER_NAME,
)
from smarter.apps.provider.services.text_completion.openai.const import (
    PROVIDER_NAME as OPENAI_PROVIDER_NAME,
)
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

    providers = [OPENAI_PROVIDER_NAME, GOOGLEAI_PROVIDER_NAME]

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)

    def get_prompt_data(self, filename: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.get_readonly_json_file(os.path.join(HERE, "data", filename)))

    def test_passthrough_openai(self):
        """Test that we can create a chat completion using the passthrough view."""

        def get_provider_config(provider_name: str):
            # /api/v1/prompts/passthrough/openai/
            url = reverse(namespace, args=[provider_name])
            prompt_data = self.get_prompt_data(f"{provider_name}_passthrough_prompt.json")

            return url, prompt_data

        for provider in self.providers:
            url, prompt_data = get_provider_config(provider)
            response = self.client.post(url, data=prompt_data, content_type="application/json")
            self.assertEqual(response.status_code, 200)

    def test_illegal_key(self):
        """Test that we get a 400 response if we include an illegal key in the request."""

        url = reverse(namespace, args=[OPENAI_PROVIDER_NAME])
        prompt_data = self.get_prompt_data("openai_passthrough_prompt.json")

        prompt_data["illegal_key"] = "illegal_value"
        url = reverse(namespace, args=[OPENAI_PROVIDER_NAME])
        response = self.client.post(url, data=prompt_data, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        logger.debug(
            "Received response with status code: %s and content: %s",
            response.status_code,
            formatted_json(response.json()),
        )
