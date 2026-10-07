# pylint: disable=W0613
"""Test the error and fallback branches of the prompt passthrough view, with the provider handler faked."""

from http import HTTPStatus
from unittest.mock import MagicMock, patch

from django.test import Client
from openai.types.chat.chat_completion import ChatCompletion

from smarter.apps.account.models import SmarterBudgetExceeded, UserProfile
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.prompt.api.v1.views import passthrough
from smarter.apps.prompt.api.v1.views.tests.test_passthrough import namespace
from smarter.apps.provider.models import Provider
from smarter.lib.django.http.shortcuts import SmarterHttpResponseBadRequest
from smarter.lib.django.shortcuts import reverse

MODULE = "smarter.apps.prompt.api.v1.views.passthrough"


def chat_completion() -> ChatCompletion:
    """A minimal ChatCompletion, as a provider handler returns it."""
    return ChatCompletion(id="chatcmpl-test", choices=[], created=0, model="test-model", object="chat.completion")


class TestPassthroughViewBranches(TestAccountMixin):
    """Test the passthrough view's handling of each outcome of the provider handler."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.client.force_login(self.admin_user)
        self.url = reverse(namespace, args=["openai"])

    def post(self, handler=None, data: str = '{"model": "test-model"}'):
        """POST to the passthrough endpoint with the provider handler replaced by ``handler``."""
        with patch(f"{MODULE}.openai_compatible_client.get_passthrough_handler", return_value=handler):
            return self.client.post(self.url, data=data, content_type="application/json")

    def test_should_log_follows_the_waffle_switch(self):
        self.assertIsInstance(passthrough.should_log(10), bool)

    def test_chat_completion_is_returned_as_json(self):
        response = self.post(handler=MagicMock(return_value=chat_completion()))
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertIn("chatcmpl-test", response.content.decode())

    def test_error_response_from_handler_is_returned_as_is(self):
        handler = MagicMock(side_effect=lambda request, *a, **kw: SmarterHttpResponseBadRequest(request, "nope"))
        response = self.post(handler=handler)
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_handler_exception_is_a_bad_request(self):
        response = self.post(handler=MagicMock(side_effect=ValueError("boom")))
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertEqual(response.json()["error"]["errorClass"], "ValueError")

    def test_unexpected_handler_return_type_raises(self):
        with self.assertRaises(Exception):
            self.post(handler=MagicMock(return_value="not a chat completion"))

    def test_invalid_json_body_is_a_bad_request(self):
        response = self.post(handler=MagicMock(), data="{not json")
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_unknown_provider_fails_the_request(self):
        with patch(
            f"{MODULE}.openai_compatible_client.get_passthrough_handler", side_effect=Provider.DoesNotExist("nope")
        ):
            response = self.client.post(self.url, data="{}", content_type="application/json")
        self.assertGreaterEqual(response.status_code, 400)

    def test_budget_exceeded_is_payment_required(self):
        with patch(f"{MODULE}.charge_authorization", side_effect=SmarterBudgetExceeded("over budget")):
            response = self.post(handler=MagicMock())
        self.assertEqual(response.status_code, HTTPStatus.PAYMENT_REQUIRED)
        self.assertEqual(response.json()["error"], "budget_exceeded")

    def fake_user_profile_model(self, get_side_effect, first=None) -> MagicMock:
        """A stand-in for the UserProfile model whose lookups fail as given."""
        fake = MagicMock()
        fake.DoesNotExist = UserProfile.DoesNotExist
        fake.MultipleObjectsReturned = UserProfile.MultipleObjectsReturned
        fake.objects.get.side_effect = get_side_effect
        fake.objects.filter.return_value.first.return_value = first
        return fake

    def test_missing_user_profile_is_forbidden(self):
        with patch(f"{MODULE}.UserProfile", self.fake_user_profile_model(UserProfile.DoesNotExist())):
            response = self.post(handler=MagicMock())
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_multiple_user_profiles_without_a_first_is_forbidden(self):
        with patch(f"{MODULE}.UserProfile", self.fake_user_profile_model(UserProfile.MultipleObjectsReturned())):
            response = self.post(handler=MagicMock())
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_multiple_user_profiles_selects_the_first(self):
        fake = self.fake_user_profile_model(UserProfile.MultipleObjectsReturned(), first=self.user_profile)
        with patch(f"{MODULE}.UserProfile", fake):
            response = self.post(handler=MagicMock(return_value=chat_completion()))
        self.assertEqual(response.status_code, HTTPStatus.OK)
