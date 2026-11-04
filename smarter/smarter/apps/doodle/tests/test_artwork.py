"""Test :mod:`smarter.apps.doodle.artwork`."""

import unittest

from smarter.apps.doodle.artwork import (
    compose_svg,
    parse_svg,
    read_base_scene,
    still_svg,
    svg_sha256,
)
from smarter.apps.doodle.const import PROPS_PLACEHOLDER_ID, VIEWBOX
from smarter.common.exceptions import SmarterValueError

PROPS = (
    '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 340">'
    '<circle id="test-sun" cx="40" cy="40" r="10" fill="#ffc145" />'
    "</svg>"
)


class TestArtwork(unittest.TestCase):
    """A theme's props are drawn on the base scene."""

    def test_base_scene(self):
        scene = parse_svg(read_base_scene())
        self.assertEqual(scene.get("viewBox"), VIEWBOX)
        self.assertIn(f'id="{PROPS_PLACEHOLDER_ID}"', read_base_scene())

    def test_compose_moves_the_props_into_the_placeholder(self):
        svg = compose_svg(PROPS, "A sun.")
        self.assertTrue(svg.startswith('<svg xmlns="http://www.w3.org/2000/svg"'))
        self.assertNotIn("ns0:", svg)
        placeholder = svg.index(f'id="{PROPS_PLACEHOLDER_ID}"')
        self.assertGreater(svg.index('id="test-sun"'), placeholder)
        self.assertIn("<title>A sun.</title>", svg)
        self.assertEqual(svg.count("<title>"), 1)

    def test_compose_without_props(self):
        svg = compose_svg("  ", "The base scene.")
        self.assertIn("<title>The base scene.</title>", svg)
        self.assertIn(f'<g id="{PROPS_PLACEHOLDER_ID}" />', svg)

    def test_invalid_props(self):
        cases = [
            "<svg",
            '<html xmlns="http://www.w3.org/1999/xhtml" />',
            '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100" />',
            '<!DOCTYPE svg [<!ENTITY x "x">]><svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 520 340">&x;</svg>',
        ]
        for props in cases:
            with self.subTest(props=props):
                with self.assertRaises(SmarterValueError):
                    compose_svg(props, "Invalid.")

    def test_still_svg(self):
        svg = compose_svg(PROPS, "A sun.")
        still = still_svg(svg)
        self.assertTrue(still.endswith("<style>*{animation:none !important;}</style></svg>"))
        self.assertEqual(still_svg("not an svg"), "not an svg")

    def test_svg_sha256(self):
        self.assertEqual(len(svg_sha256("<svg />")), 64)
        self.assertEqual(svg_sha256("<svg />"), svg_sha256("<svg />"))
        self.assertNotEqual(svg_sha256("<svg />"), svg_sha256("<svg/>"))
