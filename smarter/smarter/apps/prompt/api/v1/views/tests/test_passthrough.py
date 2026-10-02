# pylint: disable=W0613,W0718
"""Test prompt API prompt passthrough view."""

import os
from typing import Any, Optional, cast

from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as smarter_apps_api_namespace
from smarter.apps.api.v1.const import namespace as smarter_apps_api_v1_namespace
from smarter.apps.prompt.api.v1.urls import PromptAPINamespace
from smarter.apps.prompt.const import namespace as smarter_apps_prompt_namespace
from smarter.apps.provider.models import Provider
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib import logging
from smarter.lib.django.shortcuts import reverse

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

# exceptions of the provider's (OpenAI-compatible) client when it rejects our api key
UPSTREAM_CREDENTIAL_ERRORS = ("AuthenticationError", "PermissionDeniedError")

logger = logging.getLogger(__name__)


class TestPassthroughView(TestAccountMixin):
    """Test prompt API prompt passthrough view."""

    providers = Provider.objects.filter(is_active=True).values_list("name", flat=True)

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)

    @staticmethod
    def get_error_class(response) -> Optional[str]:
        """The class of the exception in a Smarter json error response, if any."""
        try:
            return response.json().get("error", {}).get("errorClass")
        except (ValueError, AttributeError):
            return None

    def get_prompt_data(self, filename: str) -> dict[str, Any]:
        return cast(dict[str, Any], self.get_readonly_json_file(os.path.join(HERE, "data", filename)))

    def test_passthrough_providers(self):
        """Test that we can create a prompt completion using the passthrough view."""

        def get_provider_config(provider_name: str):
            # /api/v1/prompts/passthrough/openai/
            url = reverse(namespace, args=[provider_name])
            prompt_data = self.get_prompt_data(f"{provider_name}_passthrough_prompt.json")

            return url, prompt_data

        for provider in self.providers:
            provider = provider.lower()
            # only the providers that have a test prompt in ./data
            if not os.path.exists(os.path.join(HERE, "data", f"{provider}_passthrough_prompt.json")):
                continue
            with self.subTest(provider=provider):
                url, prompt_data = get_provider_config(provider)
                response = self.client.post(url, data=prompt_data, content_type="application/json")
                error_class = self.get_error_class(response) if response.status_code != 200 else None
                if error_class in UPSTREAM_CREDENTIAL_ERRORS:
                    # the provider rejected our api key: an environment problem, not a code defect.
                    self.skipTest(f"{provider} rejected its api key ({error_class}). Update the key to run this test.")
                self.assertEqual(response.status_code, 200)

    def test_illegal_key(self):
        """Test that we get a 400 response if we include an illegal key in the request."""
        openai_provider_name = "openai"
        # /api/v1/prompts/passthrough/openai/
        url = reverse(namespace, args=[openai_provider_name])
        prompt_data = self.get_prompt_data("openai_passthrough_prompt.json")

        prompt_data["illegal_key"] = "illegal_value"
        url = reverse(namespace, args=[openai_provider_name])
        response = self.client.post(url, data=prompt_data, content_type="application/json")
        self.assertEqual(response.status_code, 400)
        logger.debug(
            "Received response with status code: %s and content: %s",
            response.status_code,
            formatted_json(response.json()),
        )
