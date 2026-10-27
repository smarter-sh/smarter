"""
An extension's settings: declared in its manifest, configured by an administrator.

:func:`resolve_settings` turns an extension's :class:`~smarter.apps.llmtool.models.ExtensionSetting`
rows into a typed Pydantic model, with one attribute per declared setting, which reaches
the extension's code as :attr:`~.protocol.ExtensionContext.settings`. A ``secret`` setting
is a :class:`pydantic.SecretStr`, read from its :class:`~smarter.apps.secret.models.Secret`
at call time and never cached.
"""

from typing import TYPE_CHECKING, Optional, Union

from pydantic import BaseModel, ConfigDict, SecretStr, create_model

from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .manifest import (
    ExtensionManifest,
    ExtensionSettingSpec,
    ExtensionSettingType,
    SettingValue,
)

if TYPE_CHECKING:
    from smarter.apps.llmtool.models import Extension, ExtensionSetting

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.EXTENSION_LOGGING])
logger_prefix = logging.SmarterFormattedText.text(__name__)

PYTHON_TYPES: dict[ExtensionSettingType, type] = {
    ExtensionSettingType.STRING: str,
    ExtensionSettingType.INTEGER: int,
    ExtensionSettingType.FLOAT: float,
    ExtensionSettingType.BOOLEAN: bool,
    ExtensionSettingType.URL: str,
    ExtensionSettingType.CHOICE: str,
    ExtensionSettingType.SECRET: SecretStr,
}

ResolvedSettingValue = Union[SettingValue, SecretStr, None]
"""The value of a setting as an extension's code sees it."""


class ExtensionSettingsBase(BaseModel):
    """The base class of every extension's settings model.

    Settings cannot be changed by the extension.
    """

    model_config = ConfigDict(frozen=True, extra="forbid")


def settings_model(manifest: ExtensionManifest) -> type[ExtensionSettingsBase]:
    """
    Return the Pydantic model of an extension's settings.

    :param manifest: The extension's manifest.
    :returns: A model with one optional attribute per declared setting.
    """
    fields: dict[str, tuple[type, None]] = {
        spec.name: (Optional[PYTHON_TYPES[spec.type]], None) for spec in manifest.smarter.settings  # type: ignore[misc]
    }
    class_name = "".join(part.title() for part in manifest.slug.split("-")) + "Settings"
    return create_model(class_name, __base__=ExtensionSettingsBase, **fields)  # type: ignore[call-overload]


def setting_value(spec: ExtensionSettingSpec, row: Optional["ExtensionSetting"]) -> ResolvedSettingValue:
    """
    Return the value of one setting: the configured value, or the default.

    :param spec: The setting's declaration.
    :param row: Its configured value, if any.
    :returns: The value, as the setting's type, or None if it has neither a value nor a default.
    """
    if spec.type == ExtensionSettingType.SECRET:
        if row is None or row.secret is None:
            return None
        value = row.secret.get_secret()
        return SecretStr(value) if value else None
    if row is not None and row.value != "":
        try:
            return spec.coerce(row.value)
        except ValueError as e:
            logger.error("%s.setting_value() ignoring invalid value of %s: %s", logger_prefix, row, e)
    return spec.default


def resolve_settings(extension: "Extension", manifest: ExtensionManifest) -> ExtensionSettingsBase:
    """
    Return an extension's settings, as its code sees them.

    :param extension: The extension.
    :param manifest: The manifest of the version that runs.
    :returns: The settings model, with every declared setting's value.
    """
    rows = {row.name: row for row in extension.settings.select_related("secret").all()}  # type: ignore[attr-defined]
    values = {spec.name: setting_value(spec, rows.get(spec.name)) for spec in manifest.smarter.settings}
    return settings_model(manifest)(**values)


def missing_required_settings(extension: "Extension", manifest: ExtensionManifest) -> list[str]:
    """
    Return the names of the required settings that have neither a value nor a default.

    An extension cannot be enabled while any are missing.

    :param extension: The extension.
    :param manifest: The manifest of the version that runs.
    """
    rows = {row.name: row for row in extension.settings.select_related("secret").all()}  # type: ignore[attr-defined]
    missing = []
    for spec in manifest.smarter.settings:
        if not spec.required:
            continue
        row = rows.get(spec.name)
        if spec.type == ExtensionSettingType.SECRET:
            if row is None or row.secret is None:
                missing.append(spec.name)
        elif (row is None or row.value == "") and spec.default is None:
            missing.append(spec.name)
    return missing


__all__ = [
    "ExtensionSettingsBase",
    "missing_required_settings",
    "resolve_settings",
    "setting_value",
    "settings_model",
]
