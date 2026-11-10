"""Test :mod:`smarter.apps.doodle.api.v1.views`, the public doodle api."""

import datetime
from http import HTTPStatus
from unittest.mock import patch

from django.test import Client
from waffle.testutils import override_switch

from smarter.apps.doodle.api.v1 import views
from smarter.apps.doodle.api.v1.urls import DoodleApiV1ReverseViews
from smarter.apps.doodle.caching import artwork_url, doodle_of_the_day
from smarter.apps.doodle.const import DEFAULT_THEME_SLUG, LEARN_HOW_URL
from smarter.apps.doodle.contract.models import DoodleApiResponse
from smarter.apps.doodle.models import Doodle, DoodleSource
from smarter.apps.doodle.planner import plan_doodle
from smarter.apps.doodle.regions import DoodleRegion
from smarter.lib.django.shortcuts import reverse
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .mixins import DIWALI, DoodleTestMixin

REGIONAL = SmarterWaffleSwitches.ENABLE_DOODLE_REGIONAL
ANIMATION = SmarterWaffleSwitches.ENABLE_DOODLE_ANIMATION
CAPTION = SmarterWaffleSwitches.ENABLE_DOODLE_CAPTION
AI_CREDIT = SmarterWaffleSwitches.ENABLE_DOODLE_AI_CREDIT

KOLKATA = "Asia/Kolkata"


class TestDoodleViews(DoodleTestMixin):
    """The doodle of the day, and its artwork, are public."""

    today_url: str

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        for region in DoodleRegion.values:
            plan_doodle(DIWALI, region)
        cls.today_url = reverse(DoodleApiV1ReverseViews.namespace, DoodleApiV1ReverseViews.today)

    def setUp(self):
        super().setUp()
        self.client = Client()
        doodle_of_the_day.invalidate(DIWALI.isoformat(), DoodleRegion.SOUTH_ASIA)
        doodle_of_the_day.invalidate(DIWALI.isoformat(), DoodleRegion.GLOBAL)
        doodle_of_the_day.invalidate(DIWALI.isoformat(), DoodleRegion.MX)

    def get_today(self, tz: str):
        """GET the doodle of Diwali, for a time zone."""
        with patch.object(views, "local_date", return_value=DIWALI):
            response = self.client.get(self.today_url, {"tz": tz})
        self.assertEqual(response.status_code, HTTPStatus.OK)
        return response

    def test_the_url(self):
        self.assertEqual(self.today_url, "/api/v1/doodles/today/")
        self.assertTrue(artwork_url("a" * 64).startswith("/api/v1/doodles/artwork/aaaa"))

    def test_today_in_a_region(self):
        with override_switch(REGIONAL, active=True), override_switch(CAPTION, active=True):
            with override_switch(ANIMATION, active=True):
                response = self.get_today(KOLKATA)
        body = DoodleApiResponse.model_validate(response.json())
        self.assertEqual(body.theme, "diwali")
        self.assertEqual(body.region, DoodleRegion.SOUTH_ASIA)
        self.assertEqual(body.date, DIWALI.isoformat())
        self.assertTrue(body.show_caption)
        self.assertTrue(body.animated)
        self.assertFalse(body.is_default)
        self.assertNotIn("still", body.image_url)
        self.assertIn("imageUrl", response.json())
        self.assertEqual(response["Cache-Control"], "public, max-age=300")

    def test_today_elsewhere_is_the_default(self):
        with override_switch(REGIONAL, active=True), override_switch(CAPTION, active=True):
            response = self.get_today("America/Mexico_City")
        body = DoodleApiResponse.model_validate(response.json())
        self.assertEqual(body.theme, DEFAULT_THEME_SLUG)
        self.assertTrue(body.is_default)
        self.assertFalse(body.show_caption)

    def test_every_visitor_sees_the_global_doodle_while_regional_is_off(self):
        with override_switch(REGIONAL, active=False):
            response = self.get_today("America/Mexico_City")
        body = DoodleApiResponse.model_validate(response.json())
        self.assertEqual(body.region, DoodleRegion.GLOBAL)
        self.assertEqual(body.theme, "diwali")

    def test_the_ai_credit_and_its_switch(self):
        doodle = Doodle.objects.get(date=DIWALI, region=DoodleRegion.SOUTH_ASIA)
        Doodle.objects.filter(pk=doodle.pk).update(source=DoodleSource.LLM)
        self.addCleanup(Doodle.objects.filter(pk=doodle.pk).update, source=doodle.source)
        doodle_of_the_day.invalidate(DIWALI.isoformat(), DoodleRegion.SOUTH_ASIA)
        self.addCleanup(doodle_of_the_day.invalidate, DIWALI.isoformat(), DoodleRegion.SOUTH_ASIA)
        with override_switch(REGIONAL, active=True), override_switch(AI_CREDIT, active=True):
            body = self.get_today(KOLKATA).json()
        self.assertEqual(body["aiCredit"], "chosen")
        self.assertEqual(body["learnHowUrl"], LEARN_HOW_URL)
        with override_switch(REGIONAL, active=True), override_switch(AI_CREDIT, active=False):
            body = self.get_today(KOLKATA).json()
        self.assertEqual(body["aiCredit"], "")

    def test_switches_stop_animation_and_caption(self):
        with override_switch(REGIONAL, active=True), override_switch(CAPTION, active=False):
            with override_switch(ANIMATION, active=False):
                response = self.get_today(KOLKATA)
        body = DoodleApiResponse.model_validate(response.json())
        self.assertFalse(body.animated)
        self.assertFalse(body.show_caption)
        self.assertTrue(body.image_url.endswith("?still=1"))

    def test_the_artwork(self):
        theme = self.theme("diwali")
        url = artwork_url(theme.artwork.sha256)
        response = self.client.get(url)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response["Content-Type"], "image/svg+xml")
        self.assertIn("immutable", response["Cache-Control"])
        self.assertIn("sandbox", response["Content-Security-Policy"])
        self.assertEqual(response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(response.content.decode(), theme.artwork.svg)

    def test_the_still_artwork(self):
        theme = self.theme("diwali")
        response = self.client.get(artwork_url(theme.artwork.sha256), {"still": "1"})
        self.assertIn("animation:none", response.content.decode())

    def test_an_unknown_artwork(self):
        response = self.client.get(artwork_url("0" * 64))
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_the_date_is_the_visitors(self):
        now = datetime.datetime(2035, 10, 29, 20, 0, tzinfo=datetime.timezone.utc)
        with patch("smarter.apps.doodle.regions.timezone.now", return_value=now):
            response = self.client.get(self.today_url, {"tz": KOLKATA})
        self.assertEqual(response.json()["date"], DIWALI.isoformat())
