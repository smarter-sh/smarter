"""
Test :class:`smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView`, the prompt workbench page.

The page's rendering for a signed-in user is tested in ``test_views.py``, with the rest of the LLMClient dashboard views.
"""

from http import HTTPStatus
from urllib.parse import parse_qs, urlparse

from django.test import Client

from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.common.conf import smarter_settings
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase

PLATFORM_HOST = urlparse(smarter_settings.environment_platform_url).netloc


class TestPromptWorkbenchView(SmarterTestBase):
    """Test the prompt workbench page for a visitor who is not signed in."""

    def test_anonymous_visitor_is_redirected_to_sign_in(self):
        """Test that a signed-out visitor of a workbench url is redirected to the sign-in page, not refused with a 403."""
        # the redirect happens before the LLMClient is looked up, so an unsaved one's url is enough.
        url = reverse(
            f"{PromptReverseNames.namespace}:{PromptReverseNames.chat_by_hashed_id}",
            kwargs={"hashed_id": LLMClient(id=999999999).hashed_id},
        )
        response = Client().get(url, HTTP_HOST=PLATFORM_HOST)
        self.assertEqual(response.status_code, HTTPStatus.FOUND, response.content[:500])
        # login_required adds ?next=, which returns the visitor to the workbench after signing in.
        location = urlparse(response["Location"])
        self.assertEqual(location.path, "/login/")
        self.assertEqual(parse_qs(location.query).get("next"), [url])
