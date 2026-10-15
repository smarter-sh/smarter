"""Tests of smarter.apps.llmtool.extension.manifest."""

from smarter.apps.llmtool.extension.exceptions import SmarterExtensionManifestError
from smarter.apps.llmtool.extension.manifest import (
    ExtensionManifest,
    ExtensionSettingSpec,
    ExtensionSettingType,
    ExtensionSwitchSpec,
    is_development_version,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from .mixins import fixture_source

MINIMAL = """
[project]
name = "smarter-extension-minimal"
version = "0.1.0"

[tool.smarter]
slug = "minimal"
package = "minimal"
tools = ["minimal.tools:Tool"]
"""


def manifest_text(**smarter_table: str) -> str:
    """Return MINIMAL with some [tool.smarter] lines replaced or added."""
    lines = MINIMAL.strip().splitlines()
    for key, value in smarter_table.items():
        lines = [line for line in lines if not line.startswith(f"{key} =")]
        lines.append(f"{key} = {value}")
    return "\n".join(lines)


class TestExtensionManifest(SmarterTestBase):
    """Test parsing and validating an extension's pyproject.toml."""

    def test_fixture_manifest(self):
        """The echo fixture's manifest parses, with its settings, switches and lifecycle."""
        manifest = ExtensionManifest.from_pyproject((fixture_source("echo") / "pyproject.toml").read_text())
        self.assertEqual(manifest.slug, "echo")
        self.assertEqual(manifest.version, "1.0.0")
        self.assertEqual(manifest.display_name, "Echo")
        self.assertEqual(manifest.project.license, "AGPL-3.0")
        self.assertEqual(str(manifest.project.authors[0]), "Smarter Team <test@example.com>")
        self.assertEqual(manifest.smarter.timeout, 2)
        self.assertEqual(manifest.smarter.lifecycle, "echo.lifecycle:Lifecycle")
        self.assertEqual([switch.name for switch in manifest.smarter.switches], ["verbose"])
        self.assertEqual(manifest.setting("repeat").default, 1)  # type: ignore[union-attr]
        self.assertIsNone(manifest.setting("nope"))
        self.assertEqual(manifest.compatibility_problems(), [])

    def test_minimal_manifest(self):
        """A manifest needs only a name, a version, a slug, a package and a tool."""
        manifest = ExtensionManifest.from_pyproject(MINIMAL)
        self.assertEqual(manifest.display_name, "Minimal")
        self.assertEqual(manifest.smarter.timeout, 30)
        self.assertEqual(manifest.smarter.settings, [])

    def test_license_table(self):
        """The older {text = ...} license table is accepted."""
        text = MINIMAL.replace('version = "0.1.0"', 'version = "0.1.0"\nlicense = { text = "MIT" }')
        self.assertEqual(ExtensionManifest.from_pyproject(text).project.license, "MIT")

    def test_invalid_toml(self):
        """Text that is not TOML is rejected."""
        with self.assertRaises(SmarterExtensionManifestError):
            ExtensionManifest.from_pyproject("[project")

    def test_missing_tables(self):
        """[project] and [tool.smarter] are both required."""
        with self.assertRaisesRegex(SmarterExtensionManifestError, r"\[tool.smarter\]"):
            ExtensionManifest.from_pyproject('[project]\nname = "x"\nversion = "1"')
        with self.assertRaisesRegex(SmarterExtensionManifestError, r"\[project\]"):
            ExtensionManifest.from_pyproject('[tool.smarter]\nslug = "x"')

    def test_invalid_values(self):
        """Invalid slugs, packages, versions, entry points and specifiers are rejected, with the field that is wrong."""
        cases = {
            "slug": '"Not_A_Slug"',
            "package": '"not-a-package"',
            "tools": '["somewhere.else:Tool"]',
            "lifecycle": '"minimal.lifecycle"',
            "requires-smarter": '"not a specifier"',
            "timeout": "0",
        }
        for key, value in cases.items():
            with self.subTest(key=key):
                with self.assertRaisesRegex(SmarterExtensionManifestError, "smarter"):
                    ExtensionManifest.from_pyproject(manifest_text(**{key: value}))
        for project_line in ('version = "not a version"', 'dependencies = ["not a requirement!"]'):
            with self.subTest(project_line=project_line):
                text = MINIMAL.replace(
                    'version = "0.1.0"',
                    project_line if "version" in project_line else f'version = "0.1.0"\n{project_line}',
                )
                with self.assertRaises(SmarterExtensionManifestError):
                    ExtensionManifest.from_pyproject(text)

    def test_duplicates(self):
        """Tools, settings and switches must be unique."""
        with self.assertRaisesRegex(SmarterExtensionManifestError, "duplicate tools"):
            ExtensionManifest.from_pyproject(manifest_text(tools='["minimal.tools:Tool", "minimal.tools:Tool"]'))
        text = MINIMAL + '\n[[tool.smarter.settings]]\nname = "a"\n[[tool.smarter.settings]]\nname = "a"\n'
        with self.assertRaisesRegex(SmarterExtensionManifestError, "duplicate settings"):
            ExtensionManifest.from_pyproject(text)

    def test_compatibility_problems(self):
        """Every unmet requirement is explained."""
        manifest = ExtensionManifest.from_pyproject((fixture_source("incompatible") / "pyproject.toml").read_text())
        problems = manifest.compatibility_problems()
        self.assertEqual(len(problems), 3, problems)
        self.assertTrue(any("requires Python" in problem for problem in problems))
        self.assertTrue(any("not installed" in problem for problem in problems))
        self.assertTrue(any("but this platform has pydantic" in problem for problem in problems))

    def test_requires_smarter(self):
        """A released Smarter must satisfy requires-smarter; an unreleased build satisfies every specifier."""
        manifest = ExtensionManifest.from_pyproject(manifest_text(**{"requires-smarter": '">=0.27,<1.0"'}))
        self.assertEqual(manifest.compatibility_problems("0.27.1"), [])
        self.assertIn("requires Smarter", manifest.compatibility_problems("1.2.0")[0])
        self.assertEqual(manifest.compatibility_problems("9999.9999.9999.dev9999"), [])

    def test_dependency_markers(self):
        """A dependency whose environment marker does not apply is not checked."""
        text = MINIMAL.replace(
            'version = "0.1.0"', 'version = "0.1.0"\ndependencies = ["nonexistent-package; python_version < \'3\'"]'
        )
        self.assertEqual(ExtensionManifest.from_pyproject(text).compatibility_problems(), [])

    def test_is_development_version(self):
        """Unreleased and unparsable versions count as development builds."""
        self.assertTrue(is_development_version("9999.9999.9999.dev9999"))
        self.assertTrue(is_development_version("not a version"))
        self.assertFalse(is_development_version("0.26.5"))


class TestExtensionSettingSpec(SmarterTestBase):
    """Test the declaration and coercion of extension settings."""

    def test_coerce(self):
        """Values, which may be text from a form, are converted to the setting's type."""
        cases = [
            (ExtensionSettingType.INTEGER, "3", 3),
            (ExtensionSettingType.FLOAT, "1.5", 1.5),
            (ExtensionSettingType.BOOLEAN, "yes", True),
            (ExtensionSettingType.BOOLEAN, "off", False),
            (ExtensionSettingType.BOOLEAN, True, True),
            (ExtensionSettingType.URL, "https://example.com/x", "https://example.com/x"),
            (ExtensionSettingType.STRING, 5, "5"),
        ]
        for setting_type, value, expected in cases:
            with self.subTest(setting_type=setting_type, value=value):
                self.assertEqual(ExtensionSettingSpec(name="s", type=setting_type).coerce(value), expected)

    def test_coerce_rejects(self):
        """Values that cannot be converted are rejected."""
        cases = [
            (ExtensionSettingType.INTEGER, True),
            (ExtensionSettingType.INTEGER, "x"),
            (ExtensionSettingType.FLOAT, False),
            (ExtensionSettingType.BOOLEAN, "maybe"),
            (ExtensionSettingType.URL, "ftp://example.com"),
        ]
        for setting_type, value in cases:
            with self.subTest(setting_type=setting_type, value=value):
                with self.assertRaises(ValueError):
                    ExtensionSettingSpec(name="s", type=setting_type).coerce(value)
        choice = ExtensionSettingSpec(name="s", type=ExtensionSettingType.CHOICE, choices=["a", "b"])
        self.assertEqual(choice.coerce("a"), "a")
        with self.assertRaises(ValueError):
            choice.coerce("c")

    def test_validation(self):
        """Names must be identifiers, choices need choices, secrets have no default, and defaults must be valid."""
        for kwargs in (
            {"name": "not-an-identifier"},
            {"name": "class"},
            {"name": "s", "type": ExtensionSettingType.CHOICE},
            {"name": "s", "type": ExtensionSettingType.SECRET, "default": "x"},
            {"name": "s", "type": ExtensionSettingType.INTEGER, "default": "x"},
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaises(ValueError):
                    ExtensionSettingSpec(**kwargs)
        self.assertEqual(ExtensionSettingSpec(name="s", type=ExtensionSettingType.INTEGER, default="4").default, 4)

    def test_switch_name(self):
        """A switch's name is lowercase letters, digits and underscores."""
        self.assertEqual(ExtensionSwitchSpec(name="debug_2").name, "debug_2")
        with self.assertRaises(ValueError):
            ExtensionSwitchSpec(name="Debug")
