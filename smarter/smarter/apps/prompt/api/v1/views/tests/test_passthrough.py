# pylint: disable=W0613,W0718
"""Test prompt API chat passthrough view"""

import logging
import os

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.api.const import namespace as smarter_apps_api_namespace
from smarter.apps.api.v1.const import namespace as smarter_apps_api_v1_namespace
from smarter.apps.prompt.api.v1.urls import PromptAPINamespace
from smarter.apps.prompt.const import namespace as smarter_apps_prompt_namespace

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

        # /api/v1/prompts/passthrough/openai/
        self.url = reverse(namespace, args=["openai"])
        logger.debug("Set up TestPassthroughView with namespace: %s  URL: %s", namespace, self.url)

    def test_passthrough_view(self):
        """Test that we can create a chat completion using the passthrough view."""
