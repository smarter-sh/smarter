"""Test OpenAICompatibleClientFactory, in smarter.apps.provider.services.text_completion.providers."""

from unittest.mock import MagicMock, patch

from django.contrib.auth.models import AnonymousUser
from django.test import RequestFactory

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.provider.services.text_completion.providers import (
    OpenAICompatibleClientFactory,
    smarter_compatible_client,
)

MODULE = "smarter.apps.provider.services.text_completion.providers"


class TestSmarterHarness(TestAccountMixin):
    """Test get_smarter_harness(), which runs a prompt with the provider that the prompt's user may read."""

    def harness_provider_user(self, request_user):
        """Run the harness's handler for a request by request_user, and return the user it read the provider for."""
        request = RequestFactory().post("/prompt/")
        request.user = request_user
        provider = MagicMock(api_key=None)
        with (
            patch.object(
                OpenAICompatibleClientFactory, "get_client_orm_by_provider_name_and_user", return_value=provider
            ) as get_provider,
            patch(f"{MODULE}.OpenAISmarterClient") as client,
        ):
            handler = smarter_compatible_client.get_smarter_harness(request=request, provider_name="openai")
            handler(self.user_profile, MagicMock(), {"messages": []})
        client.return_value.handler.assert_called_once()
        self.assertEqual(get_provider.call_args.kwargs["provider_name"], "openai")
        return get_provider.call_args.kwargs["user"]

    def test_anonymous_request_reads_the_provider_as_the_prompts_user(self):
        """Test that an anonymous prompt on a deployed LLMClient's host reads the provider as the LLMClient's owner."""
        self.assertEqual(self.harness_provider_user(AnonymousUser()), self.user_profile.user)

    def test_authenticated_request_reads_the_provider_as_the_prompts_user(self):
        """Test that an api key's user, too, reads the provider as the prompt's user, not as themselves."""
        self.assertEqual(self.harness_provider_user(self.non_admin_user), self.user_profile.user)
