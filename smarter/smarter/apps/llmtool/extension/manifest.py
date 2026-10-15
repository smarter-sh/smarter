"""
A Smarter Extension's ``pyproject.toml``, at the root of its archive.

It is not a SAM manifest: it is a standard Python project file, which this module calls the
extension's manifest only in its class names.

An Extension describes itself with a standard ``pyproject.toml``. The ``[project]`` table
holds what any Python package declares (name, version, description, authors, license,
dependencies), and the ``[tool.smarter]`` table holds what Smarter needs: the extension's
slug, its Python package, the tools it provides, the settings an administrator must
configure, and the Smarter versions it is compatible with.

.. code-block:: toml

    [project]
    name = "smarter-weather"
    version = "1.0.0"
    description = "Current weather and a 24-hour forecast for any location."
    authors = [{ name = "Smarter Team" }]
    license = "AGPL-3.0"
    requires-python = ">=3.12"
    dependencies = ["googlemaps", "openmeteo-requests>=1.5"]

    [tool.smarter]
    slug = "weather"
    package = "weather"
    requires-smarter = ">=0.27"
    tools = ["weather.tools:GetWeather"]

    [[tool.smarter.settings]]
    name = "google_maps_api_key"
    type = "secret"
    required = true
    description = "Google Maps Geocoding API key."

Dependencies are checked, never installed: an Extension may import only what the platform
already ships. :meth:`ExtensionManifest.compatibility_problems` explains every unmet
requirement.
"""

import importlib.metadata
import keyword
import re
import sys
import tomllib
from enum import StrEnum
from typing import Optional, Union

from packaging.requirements import InvalidRequirement, Requirement
from packaging.specifiers import InvalidSpecifier, SpecifierSet
from packaging.version import InvalidVersion, Version
from pydantic import (
    BaseModel,
    ConfigDict,
    Field,
    ValidationError,
    field_validator,
    model_validator,
)

from smarter.__version__ import __version__ as smarter_version

from .exceptions import SmarterExtensionManifestError

SLUG_PATTERN = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")
"""An extension's slug: lowercase letters and digits, in words separated by single hyphens."""
MAX_SLUG_LENGTH = 32
TOOL_ENTRY_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*(\.[A-Za-z_][A-Za-z0-9_]*)*:[A-Za-z_][A-Za-z0-9_]*$")
"""A tool's entry point, ``<module>:<class>``, e.g. ``weather.tools:GetWeather``."""
DEFAULT_TIMEOUT = 30
"""Seconds that a tool call may run before its result is abandoned, unless the manifest says otherwise."""
MAX_TIMEOUT = 300
DEVELOPMENT_VERSION_MAJOR = 9999
"""The major version of an unreleased Smarter build, e.g. ``9999.9999.9999.dev9999``, which satisfies every requirement."""

SettingValue = Union[str, int, float, bool]
"""The value of an extension setting."""


class ExtensionSettingType(StrEnum):
    """The type of an extension setting, which determines its form field and its Python type."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    URL = "url"
    CHOICE = "choice"
    SECRET = "secret"


class ExtensionSettingSpec(BaseModel):
    """
    A setting that an Extension declares, and that an administrator configures.

    A ``secret`` setting's value is a :class:`~smarter.apps.secret.models.Secret`, so it is
    encrypted at rest, and reaches the extension's code as a :class:`pydantic.SecretStr`.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="The setting's name, a Python identifier, e.g. google_maps_api_key.")
    type: ExtensionSettingType = Field(ExtensionSettingType.STRING, description="The setting's type.")
    description: str = Field("", description="What the setting is for, shown to administrators.")
    default: Optional[SettingValue] = Field(None, description="The value used when none is configured.")
    required: bool = Field(False, description="Whether the extension cannot be enabled until the setting has a value.")
    choices: Optional[list[str]] = Field(None, description="The allowed values of a choice setting.")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """A setting's name must be a Python identifier, so that the extension can read it as an attribute."""
        if not v.isidentifier() or keyword.iskeyword(v):
            raise ValueError(f"setting name {v!r} is not a Python identifier")
        return v

    @model_validator(mode="after")
    def validate_type(self) -> "ExtensionSettingSpec":
        """A choice setting needs choices, a secret has no default, and a default must have the setting's type."""
        if self.type == ExtensionSettingType.CHOICE and not self.choices:
            raise ValueError(f"choice setting {self.name!r} has no choices")
        if self.type == ExtensionSettingType.SECRET and self.default is not None:
            raise ValueError(f"secret setting {self.name!r} cannot have a default")
        if self.default is not None:
            self.default = self.coerce(self.default)
        return self

    def coerce(self, value: SettingValue) -> SettingValue:
        """
        Convert a configured value, which may be text from a form, to the setting's type.

        :param value: The value.
        :returns: The value, as the setting's type.
        :raises ValueError: If the value cannot be converted.
        """
        if self.type in (ExtensionSettingType.INTEGER, ExtensionSettingType.FLOAT):
            number_type = int if self.type == ExtensionSettingType.INTEGER else float
            if isinstance(value, bool):
                raise ValueError(f"{self.name}: {value!r} is not {'an integer' if number_type is int else 'a number'}")
            try:
                return number_type(value)
            except (TypeError, ValueError) as e:
                raise ValueError(
                    f"{self.name}: {value!r} is not {'an integer' if number_type is int else 'a number'}"
                ) from e
        if self.type == ExtensionSettingType.BOOLEAN:
            if isinstance(value, bool):
                return value
            text = str(value).strip().lower()
            if text in ("true", "1", "yes", "on"):
                return True
            if text in ("false", "0", "no", "off", ""):
                return False
            raise ValueError(f"{self.name}: {value!r} is not a boolean")
        text = str(value)
        if self.type == ExtensionSettingType.URL and not re.match(r"^https?://[^\s/]+", text):
            raise ValueError(f"{self.name}: {value!r} is not an http(s) URL")
        if self.type == ExtensionSettingType.CHOICE and text not in (self.choices or []):
            raise ValueError(f"{self.name}: {value!r} is not one of {self.choices}")
        return text


class ExtensionSwitchSpec(BaseModel):
    """
    A waffle switch that an Extension owns.

    It is created, as ``ext_<slug>_<name>``, when the extension is installed, and deleted
    when it is uninstalled. The extension's code reads it with
    :meth:`~smarter.apps.llmtool.extension.protocol.ExtensionContext.switch_is_active`.
    """

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., description="The switch's name, without the ext_<slug>_ prefix, e.g. logging.")
    description: str = Field("", description="What the switch turns on.")
    default: bool = Field(False, description="Whether the switch is on when it is created.")

    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """A switch's name is lowercase letters, digits and underscores."""
        if not re.match(r"^[a-z][a-z0-9_]{0,63}$", v):
            raise ValueError(f"switch name {v!r} must be lowercase letters, digits and underscores")
        return v


class ExtensionAuthor(BaseModel):
    """An author in ``[project].authors``."""

    model_config = ConfigDict(extra="ignore")

    name: Optional[str] = None
    email: Optional[str] = None

    def __str__(self) -> str:
        if self.name and self.email:
            return f"{self.name} <{self.email}>"
        return self.name or self.email or ""


class ExtensionProject(BaseModel):
    """
    The ``[project]`` table of an extension's ``pyproject.toml``.

    Extra fields are allowed, because ``[project]`` is a Python packaging standard that
    defines more fields than Smarter reads.
    """

    model_config = ConfigDict(extra="allow", populate_by_name=True)

    name: str
    version: str
    description: str = ""
    authors: list[ExtensionAuthor] = Field(default_factory=list)
    license: Optional[str] = None
    requires_python: Optional[str] = Field(None, alias="requires-python")
    dependencies: list[str] = Field(default_factory=list)
    urls: dict[str, str] = Field(default_factory=dict)

    @field_validator("version")
    @classmethod
    def validate_version(cls, v: str) -> str:
        """The version must be a PEP 440 version, so that versions can be compared."""
        try:
            Version(v)
        except InvalidVersion as e:
            raise ValueError(f"version {v!r} is not a valid version") from e
        return v

    @field_validator("license", mode="before")
    @classmethod
    def validate_license(cls, v: Union[None, str, dict[str, str]]) -> Optional[str]:
        """Accept an SPDX expression (PEP 639), or the older ``{text = ...}`` and ``{file = ...}`` tables."""
        if isinstance(v, dict):
            return v.get("text") or v.get("file")
        return v

    @field_validator("dependencies")
    @classmethod
    def validate_dependencies(cls, v: list[str]) -> list[str]:
        """Each dependency must be a PEP 508 requirement."""
        for dependency in v:
            try:
                Requirement(dependency)
            except InvalidRequirement as e:
                raise ValueError(f"dependency {dependency!r} is not a valid requirement: {e}") from e
        return v


class ExtensionSmarterTable(BaseModel):
    """The ``[tool.smarter]`` table of an extension's ``pyproject.toml``."""

    model_config = ConfigDict(extra="forbid", populate_by_name=True)

    slug: str = Field(..., description="The extension's unique, permanent identifier, e.g. weather.")
    package: str = Field(..., description="The Python package, at the archive's root, that holds the code.")
    display_name: Optional[str] = Field(None, alias="display-name", description="The name shown to people.")
    requires_smarter: Optional[str] = Field(
        None, alias="requires-smarter", description="The Smarter versions it works with, e.g. >=0.27,<1.0."
    )
    icon: Optional[str] = Field(
        None, description="The path of its icon, relative to the package, e.g. static/icon.svg."
    )
    tools: list[str] = Field(..., min_length=1, description="The tools' entry points, as <module>:<class>.")
    settings: list[ExtensionSettingSpec] = Field(default_factory=list)
    switches: list[ExtensionSwitchSpec] = Field(default_factory=list)
    lifecycle: Optional[str] = Field(
        None, description="The entry point, <module>:<class>, of its SmarterExtensionLifecycle hooks."
    )
    timeout: int = Field(DEFAULT_TIMEOUT, ge=1, le=MAX_TIMEOUT, description="Seconds a tool call may run.")

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: str) -> str:
        """A slug is lowercase words separated by hyphens, so that it is safe in URLs, paths and function names."""
        if len(v) > MAX_SLUG_LENGTH or not SLUG_PATTERN.match(v):
            raise ValueError(
                f"slug {v!r} must be at most {MAX_SLUG_LENGTH} lowercase letters and digits, "
                "in words separated by single hyphens, e.g. date-calculator"
            )
        return v

    @field_validator("package")
    @classmethod
    def validate_package(cls, v: str) -> str:
        """The package must be a top-level Python package name."""
        if not v.isidentifier() or keyword.iskeyword(v):
            raise ValueError(f"package {v!r} is not a Python package name")
        return v

    @field_validator("requires_smarter")
    @classmethod
    def validate_requires_smarter(cls, v: Optional[str]) -> Optional[str]:
        """``requires-smarter`` must be a PEP 440 version specifier."""
        if v:
            try:
                SpecifierSet(v)
            except InvalidSpecifier as e:
                raise ValueError(f"requires-smarter {v!r} is not a version specifier") from e
        return v

    @model_validator(mode="after")
    def validate_tools_and_settings(self) -> "ExtensionSmarterTable":
        """Every tool must be in the extension's package, and setting names must be unique."""
        entries = list(self.tools) + ([self.lifecycle] if self.lifecycle else [])
        for entry in entries:
            if not TOOL_ENTRY_PATTERN.match(entry):
                raise ValueError(f"entry point {entry!r} must be <module>:<class>")
            module = entry.split(":", 1)[0]
            if module != self.package and not module.startswith(self.package + "."):
                raise ValueError(f"entry point {entry!r} is not in the package {self.package!r}")
        for label, names in (
            ("settings", [setting.name for setting in self.settings]),
            ("switches", [switch.name for switch in self.switches]),
            ("tools", list(self.tools)),
        ):
            duplicates = sorted({name for name in names if names.count(name) > 1})
            if duplicates:
                raise ValueError(f"duplicate {label}: {', '.join(duplicates)}")
        return self


class ExtensionManifest(BaseModel):
    """
    A Smarter Extension's manifest, parsed from its ``pyproject.toml``.

    **Example usage**::

        manifest = ExtensionManifest.from_pyproject(text)
        problems = manifest.compatibility_problems()
    """

    model_config = ConfigDict(extra="forbid")

    project: ExtensionProject
    smarter: ExtensionSmarterTable

    @classmethod
    def from_pyproject(cls, text: str) -> "ExtensionManifest":
        """
        Parse and validate the text of a ``pyproject.toml``.

        :param text: The file's text.
        :returns: The manifest.
        :raises SmarterExtensionManifestError: If the file is not valid TOML, or not a valid extension manifest.
        """
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as e:
            raise SmarterExtensionManifestError(f"pyproject.toml is not valid TOML: {e}") from e
        smarter_table = data.get("tool", {}).get("smarter")
        if smarter_table is None:
            raise SmarterExtensionManifestError("pyproject.toml has no [tool.smarter] table")
        if "project" not in data:
            raise SmarterExtensionManifestError("pyproject.toml has no [project] table")
        try:
            return cls(project=data["project"], smarter=smarter_table)
        except ValidationError as e:
            problems = "; ".join(
                f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in e.errors()
            )
            raise SmarterExtensionManifestError(f"pyproject.toml is not a valid extension manifest: {problems}") from e

    @property
    def slug(self) -> str:
        """The extension's slug."""
        return self.smarter.slug

    @property
    def version(self) -> str:
        """The extension's version, as written in the manifest."""
        return self.project.version

    @property
    def display_name(self) -> str:
        """The name shown to people: ``display-name``, or the slug in title case."""
        return self.smarter.display_name or self.slug.replace("-", " ").title()

    def setting(self, name: str) -> Optional[ExtensionSettingSpec]:
        """Return the declared setting named ``name``, or None."""
        return next((setting for setting in self.smarter.settings if setting.name == name), None)

    def compatibility_problems(self, platform_version: str = smarter_version) -> list[str]:
        """
        Explain why this extension cannot run on this platform, if it cannot.

        Checks the Python version, the Smarter version, and that every dependency is
        installed at a version that satisfies it. An unreleased Smarter build satisfies
        every ``requires-smarter``.

        :param platform_version: The Smarter version to check against.
        :returns: A description of each unmet requirement; empty if the extension is compatible.
        """
        problems: list[str] = []
        python_version = ".".join(str(part) for part in sys.version_info[:3])
        if self.project.requires_python and not SpecifierSet(self.project.requires_python).contains(
            python_version, prereleases=True
        ):
            problems.append(f"requires Python {self.project.requires_python}, but this is Python {python_version}")
        if self.smarter.requires_smarter and not is_development_version(platform_version):
            if not SpecifierSet(self.smarter.requires_smarter).contains(platform_version, prereleases=True):
                problems.append(
                    f"requires Smarter {self.smarter.requires_smarter}, but this is Smarter {platform_version}"
                )
        for dependency in self.project.dependencies:
            requirement = Requirement(dependency)
            if requirement.marker is not None and not requirement.marker.evaluate():
                continue
            try:
                installed = importlib.metadata.version(requirement.name)
            except importlib.metadata.PackageNotFoundError:
                problems.append(f"requires {dependency}, which is not installed on this platform")
                continue
            if requirement.specifier and not requirement.specifier.contains(installed, prereleases=True):
                problems.append(f"requires {dependency}, but this platform has {requirement.name} {installed}")
        return problems


def is_development_version(version: str) -> bool:
    """
    Return whether a Smarter version is an unreleased build, e.g. ``9999.9999.9999.dev9999``.

    :param version: The version.
    :returns: True for an unreleased build.
    """
    try:
        return Version(version).major >= DEVELOPMENT_VERSION_MAJOR
    except InvalidVersion:
        return True


__all__ = [
    "ExtensionAuthor",
    "ExtensionManifest",
    "ExtensionProject",
    "ExtensionSettingSpec",
    "ExtensionSettingType",
    "ExtensionSmarterTable",
    "ExtensionSwitchSpec",
    "SettingValue",
    "is_development_version",
]
