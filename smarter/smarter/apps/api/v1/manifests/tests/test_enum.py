"""Tests of smarter.apps.api.v1.manifests.enum: the SAM kinds' icons, and the order in which they are applied."""

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


class TestSAMKindsApplyOrder(SmarterTestBase):
    """Test SAMKinds.apply_order() and SAMKinds.apply_rank()."""

    def test_every_kind_has_a_place_in_the_order(self):
        """Each SAM kind is in the order, once, so that a new kind gets a deliberate place."""
        self.assertEqual(sorted(SAMKinds.apply_order()), sorted(SAMKinds.all()))

    def test_dependencies_come_first(self):
        """Each kind comes after the kinds that its manifests name."""
        rank = SAMKinds.apply_rank
        for dependency, dependent in (
            ("Secret", "SqlConnection"),
            ("Secret", "ApiConnection"),
            ("Secret", "Provider"),
            ("SqlConnection", "SqlPlugin"),
            ("ApiConnection", "ApiPlugin"),
            ("SqlPlugin", "LLMClient"),
            ("ApiPlugin", "LLMClient"),
            ("MCPClient", "LLMClient"),
            ("Guardrail", "LLMClient"),
            ("CustomDomain", "LLMClient"),
            ("LLMClient", "Orchestrator"),
            ("LLMClient", "Budget"),
        ):
            with self.subTest(dependency=dependency, dependent=dependent):
                self.assertLess(rank(dependency), rank(dependent))

    def test_apply_rank(self):
        """A kind is a member or its value, in any case; any other kind is applied last."""
        self.assertEqual(SAMKinds.apply_rank(SAMKinds.SECRET), SAMKinds.apply_order().index("Secret"))
        self.assertEqual(SAMKinds.apply_rank("secret"), SAMKinds.apply_rank("Secret"))
        self.assertEqual(SAMKinds.apply_rank("NoSuchKind"), len(SAMKinds.apply_order()))
