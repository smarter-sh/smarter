"""
Test :class:`smarter.apps.prompt.views.detailviews.prompt_workbench_view.PromptWorkbenchView`, the workbench's page.

The page is the single-page console's. Its access check, the resource api, and its endpoints are tested in
``test_views.py``, with the rest of the LLMClient's views, and the page itself in @smarter/console's tests.
"""

from http import HTTPStatus

from django.test import Client

from smarter.apps.dashboard.views.console_app import console_index_html
from smarter.apps.llmclient.models import LLMClient
from smarter.apps.prompt.urls import PromptReverseNames
from smarter.lib.django.shortcuts import reverse
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestPromptWorkbenchView(SmarterTestBase):
    """Test the workbench's page for a visitor who is not signed in."""

    def test_anonymous_visitor_gets_the_console(self):
        """A signed-out visitor of a workbench url gets the console's page, whose router sends them to sign in."""
        # the page doesn't look the LLMClient up, so an unsaved one's url is enough.
        url = reverse(
            f"{PromptReverseNames.namespace}:{PromptReverseNames.chat_by_hashed_id}",
            kwargs={"hashed_id": LLMClient(id=999999999).hashed_id},
        )
        response = Client().get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:500])
        self.assertIsNotNone(console_index_html())
