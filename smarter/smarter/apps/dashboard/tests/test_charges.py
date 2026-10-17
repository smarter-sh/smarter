"""Test the dashboard's Token Usage api view, :mod:`smarter.apps.dashboard.views.views.api.charges`."""

from datetime import datetime, timezone
from decimal import Decimal
from http import HTTPStatus
from uuid import uuid4

from django.test import Client, RequestFactory
from django.urls import reverse

from smarter.apps.account.models import AggregatedCharges, Charge, ChargeTypes
from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api.charges import (
    TokenUsageWindow,
    build_token_usage_series,
    requested_periodicity,
    token_usage_series,
)
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.lib import json

from ..const import namespace

NOW = datetime(2026, 10, 17, 10, 30, tzinfo=timezone.utc)


class TestTokenUsageApiView(TestAccountMixin):
    """Test ChargesView, and the series of the Token Usage chart."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.admin_user)
        self.url = reverse(f"{namespace}:{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.token_charges}")
        # a locator that no real resource has, so that no budget evaluates these charges.
        self.locator = f"userprofile-test-{uuid4().hex}"
        for periodicity in TokenUsageWindow.WINDOWS:
            self.addCleanup(token_usage_series.invalidate, self.user_profile.record_locator, periodicity)

    def post(self, body: object = None):
        data = "" if body is None else json.dumps(body)
        return self.client.post(self.url, data=data, content_type="application/json")

    def charge(self, prompt_tokens: int, completion_tokens: int, created_at: datetime) -> None:
        charge = Charge.objects.create(
            resource_locator=self.locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            total_cost=Decimal("0.01"),
        )
        self.addCleanup(charge.delete)
        # created_at is set on save, so it's moved to the time the test needs afterwards.
        Charge.objects.filter(pk=charge.pk).update(created_at=created_at)

    def aggregated(self, prompt_tokens: int, completion_tokens: int, year: int, month: int, day: int, hour: int):
        row = AggregatedCharges.objects.create(
            resource_locator=self.locator,
            charge_type=ChargeTypes.PROMPT_COMPLETION.value,
            records=1,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
            total_tokens=prompt_tokens + completion_tokens,
            total_cost=Decimal("0.02"),
            year=year,
            month=month,
            day=day,
            hour=hour,
        )
        self.addCleanup(row.delete)

    def test_each_window(self):
        """Test that each window has its number of points, of its period, oldest first."""
        for periodicity, (period, count) in TokenUsageWindow.WINDOWS.items():
            with self.subTest(periodicity=periodicity):
                response = self.post({"periodicity": periodicity})
                self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
                data = json.loads(response.content)
                self.assertEqual(data["periodicity"], periodicity)
                self.assertEqual(data["period"], period)
                self.assertEqual(len(data["points"]), count)
                starts = [point["period_start"] for point in data["points"]]
                self.assertEqual(starts, sorted(starts))

    def test_default_window(self):
        """Test that a request without a periodicity gets the last 24 hours."""
        data = json.loads(self.post().content)
        self.assertEqual(data["periodicity"], TokenUsageWindow.DAY)
        self.assertEqual(len(data["points"]), 24)

    def test_unknown_periodicity(self):
        """Test that an unknown periodicity is a 400 that names the windows."""
        response = self.post({"periodicity": "1_hour"})
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        self.assertIn("24_hours", json.loads(response.content)["error"])

    def test_counts_live_and_aggregated_charges(self):
        """Test that each point sums the charges that aren't aggregated yet, and the aggregated ones, by period."""
        self.charge(100, 50, NOW.replace(minute=5))  # this hour, not aggregated yet
        self.charge(10, 5, NOW.replace(hour=8, minute=59))
        self.aggregated(1000, 500, 2026, 10, 17, 8)
        self.aggregated(7, 7, 2026, 10, 16, 10)  # 24 hours ago: before the window
        series = build_token_usage_series(self.locator, TokenUsageWindow.DAY, now=NOW)

        by_hour = {point.period_start.hour: point for point in series.points if point.period_start.day == 17}
        self.assertEqual((by_hour[10].prompt_tokens, by_hour[10].completion_tokens), (100, 50))
        self.assertEqual((by_hour[8].prompt_tokens, by_hour[8].completion_tokens), (1010, 505))
        self.assertEqual(by_hour[8].records, 2)
        self.assertEqual(by_hour[9].total_tokens, 0)
        self.assertEqual(series.points[0].period_start, datetime(2026, 10, 16, 11, tzinfo=timezone.utc))
        self.assertEqual(sum(point.total_tokens for point in series.points), 150 + 1515)
        self.assertAlmostEqual(by_hour[8].total_cost, 0.03)

    def test_months(self):
        """Test that the year window has a point per month, ending with this one."""
        self.aggregated(40, 2, 2026, 3, 9, 0)
        series = build_token_usage_series(self.locator, TokenUsageWindow.YEAR, now=NOW)
        self.assertEqual(series.points[0].period_start, datetime(2025, 11, 1, tzinfo=timezone.utc))
        self.assertEqual(series.points[-1].period_start, datetime(2026, 10, 1, tzinfo=timezone.utc))
        march = next(point for point in series.points if point.period_start.month == 3)
        self.assertEqual(march.total_tokens, 42)

    def test_counts_the_users_own_charges(self):
        """Test that the view counts the charges to the user's UserProfile, and caches them."""
        self.locator = self.user_profile.record_locator
        before = json.loads(self.post().content)["points"][-1]["total_tokens"]
        self.charge(3, 4, datetime.now(timezone.utc))
        # cached: the new charge shows within five minutes, not at once.
        self.assertEqual(json.loads(self.post().content)["points"][-1]["total_tokens"], before)
        token_usage_series.invalidate(self.locator, TokenUsageWindow.DAY)
        self.assertEqual(json.loads(self.post().content)["points"][-1]["total_tokens"], before + 7)

    def test_unknown_window(self):
        """Test that build_token_usage_series refuses an unknown periodicity."""
        with self.assertRaises(ValueError):
            build_token_usage_series(self.locator, "2_weeks")

    def test_requested_periodicity(self):
        """Test that only a JSON object's string periodicity is read, and anything else is the default."""
        factory = RequestFactory()
        for body, expected in [
            ('{"periodicity": "7_days"}', "7_days"),
            ('{"periodicity": "nonsense"}', "nonsense"),
            ('{"periodicity": 7}', TokenUsageWindow.DEFAULT),
            ("{}", TokenUsageWindow.DEFAULT),
            ("", TokenUsageWindow.DEFAULT),
            ("not json", TokenUsageWindow.DEFAULT),
            ('["7_days"]', TokenUsageWindow.DEFAULT),
            (b"\xff", TokenUsageWindow.DEFAULT),
        ]:
            request = factory.post(self.url, data=body, content_type="application/json")
            self.assertEqual(requested_periodicity(request), expected, body)
