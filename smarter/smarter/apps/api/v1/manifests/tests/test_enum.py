"""Tests of smarter.apps.api.v1.manifests.enum: the SAM kinds' icons, and the platform's copy of SAMKinds."""

import re
from pathlib import Path

from smarter.apps.api.v1.manifests.enum import (
    SAM_KIND_ICON_DEFAULT,
    SAM_KIND_ICONS,
    SAMKinds,
    sam_kind_icon,
)
from smarter.common.const import PYTHON_ROOT
from smarter.lib.unittest.base_classes import SmarterTestBase

KEEN_ICONS_CSS = Path(PYTHON_ROOT) / "smarter" / "static" / "assets" / "plugins" / "global" / "plugins.bundle.css"
"""The web console's global stylesheet, which defines the Keen Icons."""


class TestSAMKindsIcon(SmarterTestBase):
    """Test sam_kind_icon(), and the icons of SAM_KIND_ICONS."""

    def test_every_kind_has_an_icon_of_its_own(self):
        """Every SAM kind has an icon, and no two kinds share one."""
        self.assertEqual(set(SAM_KIND_ICONS), set(SAMKinds.all()))
        icons = [sam_kind_icon(kind) for kind in SAMKinds.all()]
        self.assertEqual(len(icons), len(set(icons)), icons)
        self.assertNotIn(SAM_KIND_ICON_DEFAULT, icons)

    def test_icon(self):
        """A kind is a member or its value, in any case; any other kind has the default icon."""
        self.assertEqual(sam_kind_icon(SAMKinds.SECRET), "lock-2")
        self.assertEqual(sam_kind_icon("Secret"), "lock-2")
        self.assertEqual(sam_kind_icon("sqlplugin"), sam_kind_icon(SAMKinds.SQL_PLUGIN))
        self.assertEqual(sam_kind_icon("Extension"), SAM_KIND_ICON_DEFAULT)

    def test_icons_are_keen_icons(self):
        """Every icon, and the default, is defined by the web console's stylesheet."""
        if not KEEN_ICONS_CSS.exists():
            self.skipTest(f"{KEEN_ICONS_CSS} is not here.")
        defined = set(re.findall(r"\.ki-([a-z0-9-]+)", KEEN_ICONS_CSS.read_text(encoding="utf-8", errors="ignore")))
        for icon in [*SAM_KIND_ICONS.values(), SAM_KIND_ICON_DEFAULT]:
            self.assertIn(icon, defined, f"ki-{icon} is not a Keen icon")


class TestSAMKindsSource(SmarterTestBase):
    """SAMKinds is smarter-types' own class, which smarter-types tests, apply order included."""

    def test_samkinds_is_from_smarter_types(self):
        """The platform re-exports smarter-types' SAMKinds, rather than defining its own."""
        import smarter_types  # pylint: disable=import-outside-toplevel

        self.assertIs(SAMKinds, smarter_types.SAMKinds)
