"""Constants for the doodle app."""

import os

namespace = "doodle"

HERE = os.path.abspath(os.path.dirname(__file__))

THEMES_PATH = os.path.join(HERE, "data", "themes")
"""The folder of the theme catalog: one ``<slug>.yaml`` per theme, and the ``.svg`` of its props."""

BASE_SCENE_PATH = os.path.join(HERE, "static", "doodle", "base.svg")
"""The base scene, which every doodle draws its props on.

It is also the static fallback image.
"""

BASE_SCENE_STATIC_PATH = "doodle/base.svg"
"""The base scene's path among the static files, for ``{% static %}``."""

DEFAULT_THEME_SLUG = "default"
"""The evergreen theme, the base scene with no props, shown when no other theme is due."""

PLANNING_DAYS = 7
"""How many days ahead the planner prepares doodles, so that a week of content is always ready."""

RETENTION_DAYS = 30
"""How many days of past doodles the planner keeps, for the record."""

DOODLE_CACHE_TIMEOUT = 600
"""Seconds that a day's doodle, for one region, is cached."""

ARTWORK_CACHE_MAX_AGE = 60 * 60 * 24 * 365
"""Seconds that a browser may cache an artwork.

Its url is its content's hash, so it never changes.
"""

TODAY_CACHE_MAX_AGE = 300
"""Seconds that a browser may cache the response of the doodle of the day."""

SVG_NAMESPACE = "http://www.w3.org/2000/svg"

VIEWBOX = "0 0 520 340"
"""The coordinate system of the base scene, which every theme's props must share."""

PROPS_PLACEHOLDER_ID = "doodle-props"
"""The id of the empty group in the base scene that a theme's props are drawn into."""

EDITOR_LLMCLIENT = "smarter_doodle_editor"
"""The staff-only LLMClient of the Smarter account that chooses each region's doodle, from example-manifests."""

ARTIST_LLMCLIENT = "smarter_doodle_artist"
"""The staff-only LLMClient of the Smarter account that draws a holiday that the catalog has no theme for."""

EDITOR_MAX_ATTEMPTS = 3
"""How many times the planner asks the editor about a day, before it leaves the day to the calendar."""

MAX_OBSERVANCES_PER_REGION = 12
"""How many of a region's holidays of a day the editor is told about, at most."""

MAX_GENERATED_SVG_LENGTH = 40_000
"""The longest SVG, in characters, that the Smarter Doodle Artist may answer with."""

LEARN_HOW_URL = "https://docs.smarter.sh/en/latest/smarter-framework/developer-reference/react-integration/doodle.html"
"""Where the credit of a doodle that a Smarter AI application chose or drew links to: how it works."""
