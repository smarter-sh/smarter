"""Test the REST api's token usage, :mod:`smarter.apps.account.api.v1.views.usage`."""

from http import HTTPStatus

from rest_framework.test import APIClient

from smarter.apps.account.token_usage import TokenUsageWindow, token_usage_series
from smarter.apps.api.v1.contract.tests.mixins import OpenApiResponseMixin
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase

URL = "/api/v1/accounts/usage/"


class TestTokenUsageView(OpenApiResponseMixin, ApiV1TestBase):
    """Test GET /api/v1/accounts/usage/, with an api key."""

    def setUp(self):
        super().setUp()
        self.client = APIClient()
        self.client.credentials(HTTP_AUTHORIZATION=f"Token {self.token_key}")
        for periodicity in TokenUsageWindow.WINDOWS:
            self.addCleanup(token_usage_series.invalidate, self.user_profile.record_locator, periodicity)

    def test_default_window(self):
        """Without a periodicity, the window is the last 24 hours, by hour."""
        response = self.client.get(URL)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        data = response.json()
        self.assertValidResponse("/accounts/usage/", "get", data)
        self.assertEqual(data["periodicity"], TokenUsageWindow.DEFAULT)
        self.assertEqual(data["period"], "hour")
        self.assertEqual(len(data["points"]), 24)
        self.assertEqual(
            set(data["points"][0]),
            {"period_start", "records", "prompt_tokens", "completion_tokens", "total_tokens", "total_cost"},
        )

    def test_each_window(self):
        """Each window has its number of points, of its period."""
        for periodicity, (period, count) in TokenUsageWindow.WINDOWS.items():
            with self.subTest(periodicity=periodicity):
                response = self.client.get(URL, {"periodicity": periodicity})
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
                self.assertEqual((response.json()["period"], len(response.json()["points"])), (period, count))

    def test_unknown_window(self):
        """An unknown periodicity is a 400 that names the windows."""
        response = self.client.get(URL, {"periodicity": "1_century"})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertValidResponse("/accounts/usage/", "get", response.json(), HTTPStatus.BAD_REQUEST)
        self.assertIn("24_hours", response.json()["detail"])

    def test_anonymous(self):
        """A request without an api key is refused."""
        self.assertIn(APIClient().get(URL).status_code, (HTTPStatus.UNAUTHORIZED, HTTPStatus.FORBIDDEN))
