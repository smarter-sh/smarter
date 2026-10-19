"""Tests of smarter.apps.api.v1.manifests.enum: the SAM kinds' icons."""

import re
from pathlib import Path

from smarter.apps.api.v1.manifests.enum import (
    SAM_KIND_ICON_DEFAULT,
    SAM_KIND_ICONS,
    SAMKinds,
)
from smarter.common.const import PYTHON_ROOT
from smarter.lib.unittest.base_classes import SmarterTestBase

KEEN_ICONS_CSS = Path(PYTHON_ROOT) / "smarter" / "static" / "assets" / "plugins" / "global" / "plugins.bundle.css"
"""The web console's global stylesheet, which defines the Keen Icons."""


class TestSAMKindsIcon(SmarterTestBase):
    """Test SAMKinds.icon(), and the icons of SAM_KIND_ICONS."""

    def test_every_kind_has_an_icon_of_its_own(self):
        """Every SAM kind has an icon, and no two kinds share one."""
        self.assertEqual(set(SAM_KIND_ICONS), set(SAMKinds.all()))
        icons = [SAMKinds.icon(kind) for kind in SAMKinds.all()]
        self.assertEqual(len(icons), len(set(icons)), icons)
        self.assertNotIn(SAM_KIND_ICON_DEFAULT, icons)

    def test_icon(self):
        """A kind is a member or its value, in any case; any other kind has the default icon."""
        self.assertEqual(SAMKinds.icon(SAMKinds.SECRET), "lock-2")
        self.assertEqual(SAMKinds.icon("Secret"), "lock-2")
        self.assertEqual(SAMKinds.icon("sqlplugin"), SAMKinds.icon(SAMKinds.SQL_PLUGIN))
        self.assertEqual(SAMKinds.icon("Extension"), SAM_KIND_ICON_DEFAULT)

    def test_icons_are_keen_icons(self):
        """Every icon, and the default, is defined by the web console's stylesheet."""
        if not KEEN_ICONS_CSS.exists():
            self.skipTest(f"{KEEN_ICONS_CSS} is not here.")
        defined = set(re.findall(r"\.ki-([a-z0-9-]+)", KEEN_ICONS_CSS.read_text(encoding="utf-8", errors="ignore")))
        for icon in [*SAM_KIND_ICONS.values(), SAM_KIND_ICON_DEFAULT]:
            self.assertIn(icon, defined, f"ki-{icon} is not a Keen icon")
