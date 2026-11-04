"""
Test :mod:`smarter.apps.doodle.trends`, the Wikipedia trend signals.

The Wikimedia apis are patched with real responses, saved in ``data/wikimedia``, so no request
leaves the test.
"""

import datetime
import os
from unittest.mock import patch

from django.utils import timezone

from smarter.apps.doodle import trends
from smarter.apps.doodle.editor import has_blocked_word
from smarter.apps.doodle.trends import (
    REGION_PROJECTS,
    is_a_person,
    is_an_occasion,
    pageviews_day,
    region_trends,
    top_articles,
    wiki_site,
)
from smarter.apps.llmtool.plugin.safe_http import SafeHttpError
from smarter.lib import json
from smarter.lib.unittest.base_classes import SmarterTestBase

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "wikimedia")


def read(name: str) -> dict:
    """Read a saved Wikimedia response."""
    with open(os.path.join(DATA, name), encoding="utf-8") as file:
        return json.load(file)


def wikimedia(url: str, params=None) -> dict:
    """Answer the Wikimedia apis with the saved responses of the Spanish Wikipedia."""
    if "pageviews" in url:
        return read("top-es.json")
    return read("entities-es.json")


class TestTrends(SmarterTestBase):
    """What a region reads about becomes a trend only if a doodle may celebrate it."""

    def setUp(self):
        super().setUp()
        # each test has its own day, so that the cached top articles are its own.
        self.day = datetime.date(2030, 1, 1) + datetime.timedelta(days=self.id().__hash__() % 1000)

    def test_every_region_reads_some_editions(self):
        for region, projects in REGION_PROJECTS.items():
            with self.subTest(region=region):
                self.assertTrue(projects)
                for project in projects:
                    self.assertTrue(project.endswith(".wikipedia.org"))

    def test_region_trends(self):
        with patch.object(trends, "get_json", side_effect=wikimedia):
            found = region_trends("mx", self.day, has_blocked_word)
        titles = [trend.title for trend in found]
        self.assertIn("2026 FIFA World Cup", titles)
        self.assertIn("Solar eclipse of August 12, 2026", titles)
        for refused in ["Antonio Navarro Wolff", "2026 Toledo train collision", "WhatsApp", "Gonzalo Miró"]:
            self.assertNotIn(refused, titles)
        world_cup = found[0]
        self.assertEqual(world_cup.id, "es:Copa_Mundial_de_Fútbol_de_2026")
        self.assertEqual(world_cup.views, 80000)
        self.assertTrue(world_cup.url.startswith("https://es.wikipedia.org/wiki/"))

    def test_top_articles_skip_other_namespaces(self):
        with patch.object(trends, "get_json", side_effect=wikimedia):
            articles = top_articles("es.wikipedia.org", self.day.isoformat())
        titles = [title for title, _ in articles]
        self.assertNotIn("Wikipedia:Portada", titles)
        self.assertNotIn("Especial:Buscar", titles)
        self.assertEqual(titles[0], "Antonio_Navarro_Wolff")

    def test_a_failed_api_is_no_trend(self):
        with patch.object(trends, "get_json", side_effect=SafeHttpError("down")), patch.object(trends, "logger"):
            self.assertEqual(region_trends("ca", self.day, has_blocked_word), [])

    def test_the_day_before_until_it_is_published(self):
        day = self.day.isoformat()
        before = (self.day - datetime.timedelta(days=1)).isoformat()

        def unpublished(url, params=None):
            if self.day.strftime("/%Y/%m/%d") in url:
                raise SafeHttpError("404")
            return wikimedia(url, params)

        with patch.object(trends, "get_json", side_effect=unpublished) as get_json:
            articles = trends.latest_top_articles("es.wikipedia.org", self.day)
        self.assertTrue(articles)
        self.assertIn(before.replace("-", "/"), get_json.call_args.args[0])
        self.assertNotEqual(day, before)

    def test_get_json(self):
        response = type("Response", (), {"content": b'{"a": 1}'})()
        with patch.object(trends, "fetch", return_value=response) as fetch:
            self.assertEqual(trends.get_json("https://wikimedia.org/x"), {"a": 1})
        self.assertIn("SmarterDoodle", fetch.call_args.kwargs["headers"]["User-Agent"])
        bad = type("Response", (), {"content": b"not json"})()
        with patch.object(trends, "fetch", return_value=bad):
            with self.assertRaises(SafeHttpError):
                trends.get_json("https://wikimedia.org/x")

    def test_one_trend_per_title_and_no_dates(self):
        top = {
            "items": [
                {
                    "articles": [
                        {"article": "F1_2026", "views": 9},
                        {"article": "Formula_1_2026", "views": 8},
                        {"article": "2_November", "views": 7},
                    ]
                }
            ]
        }
        entities = {
            "entities": {
                "Q1": {
                    "labels": {"en": {"value": "2026 Formula One World Championship"}},
                    "descriptions": {"en": {"value": "77th Formula One season"}},
                    "sitelinks": {"enwiki": {"title": "F1 2026", "url": "https://en.wikipedia.org/wiki/F1_2026"}},
                },
                "Q2": {
                    "labels": {"en": {"value": "2026 Formula One World Championship"}},
                    "descriptions": {"en": {"value": "77th Formula One season"}},
                    "sitelinks": {
                        "enwiki": {"title": "Formula 1 2026", "url": "https://en.wikipedia.org/wiki/Formula_1_2026"}
                    },
                },
                "Q3": {
                    "labels": {"en": {"value": "November 2"}},
                    "descriptions": {"en": {"value": "day of the year"}},
                    "sitelinks": {"enwiki": {"title": "2 November", "url": "https://en.wikipedia.org/wiki/2_November"}},
                },
            }
        }

        def answer(url, params=None):
            return top if "pageviews" in url else entities

        with patch.object(trends, "get_json", side_effect=answer):
            found = region_trends("us", self.day, has_blocked_word)
        self.assertEqual([(trend.title, trend.views) for trend in found], [("2026 Formula One World Championship", 9)])

    def test_is_a_person(self):
        for description in [
            "Colombian engineer and politician (1948–2026)",
            "Film director, Screenwriter (1940-1997)",
            "Italian F1 driver",
            "American actor (born 1956)",
            "association football player",
        ]:
            with self.subTest(description=description):
                self.assertTrue(is_a_person(description))
        self.assertFalse(is_a_person("international association football tournament"))

    def test_is_an_occasion(self):
        for description in [
            "international association football tournament",
            "total solar eclipse",
            "Mexican celebration",
        ]:
            with self.subTest(description=description):
                self.assertTrue(is_an_occasion(description))
        for description in ["Meta Platforms-owned mobile instant messenger", "2024 film", "executive business jet"]:
            with self.subTest(description=description):
                self.assertFalse(is_an_occasion(description))

    def test_pageviews_day(self):
        self.assertEqual(pageviews_day(datetime.date(2001, 1, 2)), datetime.date(2001, 1, 1))
        today = timezone.now().date()
        far = today + datetime.timedelta(days=30)
        self.assertEqual(pageviews_day(far), today - datetime.timedelta(days=1))

    def test_wiki_site(self):
        self.assertEqual(wiki_site("es.wikipedia.org"), "eswiki")
        self.assertEqual(wiki_site("zh-yue.wikipedia.org"), "zh_yuewiki")
