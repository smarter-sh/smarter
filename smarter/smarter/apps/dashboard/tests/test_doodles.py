"""Test the dashboard's "Newest Doodles" api view, :mod:`smarter.apps.dashboard.views.views.api.doodles`."""

import datetime
from http import HTTPStatus

from django.test import Client
from django.urls import reverse

from smarter.apps.account.tests.mixins import TestAccountMixin
from smarter.apps.dashboard.views.views.api.urls import DashboardApiReverseNames
from smarter.apps.doodle.caching import newest_drawn_doodles
from smarter.apps.doodle.models import (
    Doodle,
    DoodleArtwork,
    DoodleSource,
    DoodleStatus,
    DoodleTheme,
)
from smarter.apps.doodle.tests.mixins import DoodleTestMixin
from smarter.lib import json
from smarter.lib.typing import SmarterDictType

# days years ahead, as the doodle app's tests use, that no other test or planner run touches.
DAY = datetime.date(2036, 6, 10)
TODAY = datetime.date(2036, 6, 12)


class TestNewestDoodlesApiView(TestAccountMixin, DoodleTestMixin):
    """Test NewestDoodlesView, which lists the newest approved doodles that the Smarter Doodle Artist drew."""

    def setUp(self):
        super().setUp()
        self.client = Client()
        self.addCleanup(self.client.logout)
        self.client.force_login(self.non_admin_user)
        self.url = reverse(f"{DashboardApiReverseNames.namespace}:{DashboardApiReverseNames.newest_doodles}")
        for offset in range(5):
            day = DAY + datetime.timedelta(days=offset)
            self.addCleanup(self.delete_doodles, day)
        self.drawn = self.drawn_theme()

    def drawn_theme(self) -> DoodleTheme:
        """A theme that the artist drew, with the catalog's artwork."""
        catalog = self.theme("diwali")
        theme = DoodleTheme.objects.create(
            slug=f"ai-test-{self.hash_suffix}",
            name="Fiesta Day",
            category=catalog.category,
            caption="Happy Fiesta Day!",
            alt_text="Paper flags above a Smarter LLMClient.",
            link_url="https://en.wikipedia.org/wiki/Fiesta",
            priority=0,
            regions=["mx"],
            schedule={"kind": "never"},
            props_svg=catalog.props_svg,
            artwork=catalog.artwork,
            is_active=False,
            is_generated=True,
        )
        self.addCleanup(theme.delete)
        return theme

    def doodle(self, day: datetime.date, region: str, theme: DoodleTheme, status=DoodleStatus.APPROVED) -> Doodle:
        artwork: DoodleArtwork = theme.artwork  # type: ignore[assignment]
        return Doodle.objects.create(
            date=day,
            region=region,
            theme=theme,
            artwork=artwork,
            status=status,
            source=DoodleSource.LLM,
            title=theme.name,
            caption=theme.caption,
            alt_text=theme.alt_text,
            link_url=theme.link_url,
        )

    def test_newest_drawn_doodles(self):
        """Only the approved doodles that the artist drew, up to the day, the newest first."""
        self.doodle(DAY, "mx", self.drawn)
        self.doodle(DAY + datetime.timedelta(days=1), "ca", self.drawn)
        self.doodle(DAY + datetime.timedelta(days=1), "mx", self.drawn, status=DoodleStatus.PROPOSED)
        self.doodle(DAY + datetime.timedelta(days=2), "global", self.theme("diwali"))
        self.doodle(DAY + datetime.timedelta(days=3), "mx", self.drawn)  # after TODAY
        doodles = newest_drawn_doodles(TODAY.isoformat(), 10)
        ours = [(d.date, d.region) for d in doodles if d.theme == self.drawn.slug]
        self.assertEqual(ours, [("2036-06-11", "ca"), ("2036-06-10", "mx")])
        first = doodles[0]
        self.assertEqual(first.region_name, "Canada")
        self.assertTrue(first.image_url.endswith(".svg?still=1"))
        self.assertEqual(first.ai_credit, "drawn")
        self.assertEqual(len(newest_drawn_doodles(TODAY.isoformat(), 1)), 1)

    def test_api(self):
        """Every user gets the doodles, in camelCase."""
        response = self.client.post(self.url)
        self.assertEqual(response.status_code, HTTPStatus.OK, response.content[:300])
        body: SmarterDictType = json.loads(response.content)
        self.assertIsInstance(body["doodles"], list)
        for doodle in body["doodles"]:
            self.assertIn("regionName", doodle)
            self.assertIn("imageUrl", doodle)

    def test_api_requires_a_user(self):
        anonymous = Client()
        response = anonymous.post(self.url)
        self.assertNotEqual(response.status_code, HTTPStatus.OK)
