"""Tests of smarter.apps.llmtool.extension.settings."""

from unittest.mock import MagicMock

from pydantic import SecretStr, ValidationError

from smarter.apps.llmtool.extension.manifest import (
    ExtensionSettingSpec,
    ExtensionSettingType,
)
from smarter.apps.llmtool.extension.settings import (
    missing_required_settings,
    resolve_settings,
    setting_value,
    settings_model,
)
from smarter.apps.llmtool.models import ExtensionSetting

from .mixins import ExtensionTestMixin


class TestExtensionSettings(ExtensionTestMixin):
    """Test resolving an extension's settings."""

    def test_defaults_and_values(self):
        """Unconfigured settings have their defaults; configured ones their values, as their types."""
        extension = self.install_echo()
        manifest = extension.installed_version.parsed_manifest  # type: ignore[union-attr]
        settings = resolve_settings(extension, manifest)
        self.assertEqual((settings.greeting, settings.repeat, settings.api_key), ("hello", 1, None))  # type: ignore[attr-defined]
        self.assertEqual(missing_required_settings(extension, manifest), ["api_key"])

        self.installer.configure(extension, {"repeat": "3", "api_key": self.secret("echo_settings_key", "v")})
        settings = resolve_settings(extension, manifest)
        self.assertEqual(settings.repeat, 3)  # type: ignore[attr-defined]
        self.assertIsInstance(settings.api_key, SecretStr)  # type: ignore[attr-defined]
        self.assertEqual(settings.api_key.get_secret_value(), "v")  # type: ignore[attr-defined]
        self.assertEqual(missing_required_settings(extension, manifest), [])
        with self.assertRaises(ValidationError):
            settings.repeat = 4  # type: ignore[attr-defined]

    def test_invalid_stored_value(self):
        """A stored value that is no longer valid falls back to the default."""
        extension = self.install_echo()
        ExtensionSetting.objects.create(extension=extension, name="repeat", value="many")
        settings = resolve_settings(extension, extension.installed_version.parsed_manifest)  # type: ignore[union-attr]
        self.assertEqual(settings.repeat, 1)  # type: ignore[attr-defined]

    def test_setting_value_without_rows(self):
        """A secret without a Secret, or with an empty one, is None."""
        spec = ExtensionSettingSpec(name="key", type=ExtensionSettingType.SECRET)
        self.assertIsNone(setting_value(spec, None))
        row = MagicMock(secret=MagicMock(get_secret=MagicMock(return_value="")))
        self.assertIsNone(setting_value(spec, row))

    def test_missing_required_non_secret(self):
        """A required setting without a value or default is missing."""
        extension = self.install_echo()
        manifest = extension.installed_version.parsed_manifest  # type: ignore[union-attr]
        manifest.smarter.settings.append(ExtensionSettingSpec(name="region", required=True))
        self.assertIn("region", missing_required_settings(extension, manifest))
        model = settings_model(manifest)
        self.assertEqual(model.__name__, "EchoSettings")
        self.assertIn("region", model.model_fields)
