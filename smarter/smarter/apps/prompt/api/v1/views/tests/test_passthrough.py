# pylint: disable=W0613,W0718
"""Test prompt API prompt passthrough view."""

import os
from typing import Any, Optional, cast

import openai
from django.conf import settings
from django.test import Client

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as smarter_apps_api_namespace
from smarter.apps.api.v1.const import namespace as smarter_apps_api_v1_namespace
from smarter.apps.prompt.api.v1.urls import PromptAPINamespace
from smarter.apps.prompt.const import namespace as smarter_apps_prompt_namespace
from smarter.apps.provider.models import Provider
from smarter.common.helpers.console_helpers import formatted_json
from smarter.lib import json, logging
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

# the request templates of the dashboard's prompt passthrough page (/dashboard/passthrough/)
PROMPT_TEMPLATES_PATH = os.path.join(
    settings.PROJECT_ROOT,
    "react",
    "packages",
    "smarter-prompt-passthrough",
    "src",
    "components",
    "Prompt",
    "templates.json",
)

# exceptions raised by the provider's (OpenAI-compatible) client when the provider itself fails
# the request: bad api key, no credits, rate limits, unknown model, outages, timeouts, rejected
# parameters, etc. Third-party providers are unreliable, so these are logged and skipped rather
# than failed. Any other error originates in Smarter, and fails the test.
UPSTREAM_ERRORS = frozenset(
    name for name, obj in list(vars(openai).items()) if isinstance(obj, type) and issubclass(obj, openai.APIError)
)

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

    @staticmethod
    def get_error_description(response) -> str:
        """The description of the error in a Smarter json error response, or the raw response content."""
        try:
            return str(response.json()["error"]["description"])
        except (ValueError, KeyError, TypeError):
            return response.content.decode("utf-8")[:1000]

    def skip_if_upstream_error(self, response, label: str):
        """Log and skip when the provider, rather than Smarter, failed the request."""
        if response.status_code == 200:
            return
        error_class = self.get_error_class(response)
        if error_class in UPSTREAM_ERRORS:
            logger.error(
                "%s: the provider failed the request (%s): %s",
                label,
                error_class,
                self.get_error_description(response),
            )
            self.skipTest(f"{label}: the provider failed the request ({error_class}).")

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
                self.skip_if_upstream_error(response, provider)
                self.assertEqual(response.status_code, 200, f"{provider}: {self.get_error_description(response)}")

    def test_passthrough_templates(self):
        """
        Test every passthrough page template against every active provider.

        The request is built exactly as the dashboard's prompt passthrough page builds it: the
        provider's default model plus the template body, posted to the provider's passthrough
        endpoint. Failures of the provider itself are logged and skipped; see UPSTREAM_ERRORS.
        """
        with open(PROMPT_TEMPLATES_PATH, encoding="utf-8") as f:
            templates = json.loads(f.read())
        self.assertTrue(templates, f"no prompt templates found in {PROMPT_TEMPLATES_PATH}")

        providers = Provider.objects.filter(is_active=True).with_read_permission_for(self.admin_user)  # type: ignore
        for provider in providers:
            for template in templates:
                with self.subTest(provider=provider.name, template=template["name"]):
                    if not provider.default_model:
                        logger.warning("%s has no default model.", provider.name)
                        self.skipTest(f"{provider.name} has no default model.")
                    url = reverse(namespace, args=[provider.rfc1034_compliant_name])
                    prompt_data = {"model": provider.default_model, **template["body"]}
                    response = self.client.post(url, data=prompt_data, content_type="application/json")
                    self.skip_if_upstream_error(response, f"{provider.name} / {template['name']}")
                    self.assertEqual(
                        response.status_code,
                        200,
                        f"{provider.name} / {template['name']}: {self.get_error_description(response)}",
                    )

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
