"""Test :mod:`smarter.apps.doodle.sanitize`, the sanitizer of the Smarter Doodle Artist's SVG."""

import os
import unittest

from smarter.apps.doodle.artwork import compose_svg
from smarter.apps.doodle.sanitize import (
    clean_style,
    css_blocks,
    extract_svg,
    sanitize_svg,
)
from smarter.common.exceptions import SmarterValueError

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "artist")


def read(name: str) -> str:
    """Read a test SVG."""
    with open(os.path.join(DATA, name), encoding="utf-8") as file:
        return file.read()


class TestSanitize(unittest.TestCase):
    """Only what a flat, decorative drawing needs is left of a generated SVG."""

    def test_a_safe_drawing_is_kept(self):
        svg = sanitize_svg(read("safe.svg"), "ai")
        self.assertIn("<style>", svg)
        self.assertNotIn("ns0:", svg)
        self.assertIn("ai-sway", svg)
        self.assertEqual(svg.count("<circle"), 2)
        compose_svg(svg, "A safe drawing.")

    def test_dangerous_elements_and_attributes_are_removed(self):
        svg = sanitize_svg(read("dangerous.svg"), "ai")
        for removed in [
            "script",
            "foreignObject",
            "onload",
            "onclick",
            "href",
            "image",
            "animate",
            "javascript",
            "url(",
            "<text",
            'id="',
            "style=",
            "dd-flow",
            "data:",
        ]:
            with self.subTest(removed=removed):
                self.assertNotIn(removed, svg)
        self.assertIn("<rect", svg)
        self.assertNotIn("xmlns:xlink", svg)

    def test_a_style_that_could_restyle_the_scene_is_removed(self):
        cases = [
            "rect { fill: red; }",
            "* { animation: none; }",
            ".dd-flow { opacity: 0; }",
            ".ai-a { display: none; }",
            "@keyframes dd-x { to { opacity: 0; } }",
            "@keyframes ai-x { bogus { opacity: 0; } }",
            "@keyframes ai-x { to { display: none; } }",
            ".ai-a { opacity: 1; } }",
            ".ai-a { opacity: 1; } stray",
            "@import 'x.css';",
            ".ai-a { background: url(x); }",
            ".ai-a { opacity }",
        ]
        for css in cases:
            with self.subTest(css=css):
                self.assertEqual(clean_style(css, "ai"), "")

    def test_a_safe_style_is_kept(self):
        css = ".ai-a, .ai-b { animation: ai-a 2s infinite; } @keyframes ai-a { from, 50% { opacity: 0; } to { opacity: 1; } }"
        self.assertEqual(clean_style(css, "ai"), css)

    def test_css_blocks(self):
        self.assertEqual(css_blocks(".a { b: c; }"), [(".a", " b: c; ")])
        with self.assertRaises(ValueError):
            css_blocks(".a { b: c;")

    def test_invalid_drawings(self):
        cases = {
            "too long": "<svg " + "x" * 50_000,
            "nothing to draw": read("empty.svg"),
            "too many elements": read("crowded.svg"),
            "another viewBox": '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 10 10"><rect /></svg>',
        }
        for case, svg in cases.items():
            with self.subTest(case=case):
                with self.assertRaises(SmarterValueError):
                    sanitize_svg(svg, "ai")

    def test_extract_svg(self):
        answer = "Here it is:\n```svg\n<svg viewBox='0 0 520 340'><rect /></svg>\n```"
        self.assertEqual(extract_svg(answer), "<svg viewBox='0 0 520 340'><rect /></svg>")
        with self.assertRaises(SmarterValueError):
            extract_svg("I can't draw that.")
