"""Test :mod:`smarter.apps.doodle.contract.models`."""

import unittest

from smarter.apps.doodle.contract.models import (
    DoodleApiResponse,
    DoodleOfTheDay,
    with_query,
)

DIWALI = DoodleOfTheDay(
    date="2026-11-08",
    region="south-asia",
    theme="diwali",
    title="Diwali",
    caption="Happy Diwali!",
    alt_text="Diyas.",
    link_url="https://en.wikipedia.org/wiki/Diwali",
    image_url="/api/v1/doodles/artwork/abc.svg",
    is_default=False,
)


class TestDoodleContract(unittest.TestCase):
    """The response is camelCase, and the switches decide how the doodle is shown."""

    def test_camel_case(self):
        response = DoodleApiResponse.from_doodle(DIWALI, animated=True, show_caption=True)
        data = response.to_json()
        self.assertEqual(data["imageUrl"], "/api/v1/doodles/artwork/abc.svg")
        self.assertTrue(data["showCaption"])
        self.assertEqual(data["altText"], "Diyas.")

    def test_still(self):
        response = DoodleApiResponse.from_doodle(DIWALI, animated=False, show_caption=True)
        self.assertEqual(response.image_url, "/api/v1/doodles/artwork/abc.svg?still=1")

    def test_no_caption_for_the_default(self):
        default = DIWALI.model_copy(update={"is_default": True})
        response = DoodleApiResponse.from_doodle(default, animated=True, show_caption=True)
        self.assertFalse(response.show_caption)

    def test_with_query(self):
        self.assertEqual(with_query("/a", None), "/a")
        self.assertEqual(with_query("/a?b=1", "c=2"), "/a?b=1&c=2")
