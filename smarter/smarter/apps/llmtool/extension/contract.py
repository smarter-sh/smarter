"""
The contract of the web console's Extensions pages: the JSON of their api, as Pydantic models.

The Extensions list and an extension's page are rendered by a React app, ``@smarter/extension-console``,
that superusers use to install, configure, update and uninstall
extensions. Their api, :mod:`smarter.apps.llmtool.extension.views`, builds every response from
these models, and validates every request with them. The JSON is camelCase.

``manage.py export_extension_console_schema`` writes the models' JSON Schema to
``extension-console.schema.json``, beside this module, from which ``@smarter/extension-console``
generates its TypeScript types. A test fails if the committed schema is out of date.

Secret settings' values never leave the platform: a secret setting says only whether it is set,
and the name of its Secret.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from pydantic.alias_generators import to_camel
from pydantic.json_schema import models_json_schema

from smarter.common.const import SMARTER_PROJECT_WEBSITE_URL
from smarter.lib.typing import SmarterDictType

from .manifest import ExtensionSettingType, SettingValue

if TYPE_CHECKING:
    from smarter.apps.account.models import Account
    from smarter.apps.llmtool.models import Extension, ExtensionVersion
    from smarter.apps.secret.models import Secret

SCHEMA_PATH = Path(__file__).parent / "extension-console.schema.json"
"""The committed JSON Schema of the contract."""
SCHEMA_ID = f"{SMARTER_PROJECT_WEBSITE_URL}/schemas/extension-console.schema.json"

TrustBadge = Literal["official", "verified", "community", "unverified"]
"""How far an extension's publisher is trusted.

See :class:`~smarter.apps.llmtool.models.ExtensionTrustBadge`.
"""
Source = Literal["registry", "upload"]
"""Where an extension was installed from."""
SettingType = Literal["string", "integer", "float", "boolean", "url", "choice", "secret"]
"""The type of an extension setting.

See :class:`~.manifest.ExtensionSettingType`.
"""
RegistryAction = Literal["install", "update", "installed", "uploaded", "incompatible"]
"""What a registry extension's card offers: install it, update it, or nothing, and why."""

TRUST_BADGE_LABELS: dict[str, str] = {
    "official": "Official Smarter Extension",
    "verified": "Verified Publisher",
    "community": "Community",
    "unverified": "Unverified",
}


class ExtensionConsoleModel(BaseModel):
    """The base class of the contract's models: camelCase JSON, and no fields that a model doesn't define."""

    model_config = ConfigDict(
        extra="forbid",
        alias_generator=to_camel,
        validate_by_name=True,
        validate_by_alias=True,
        serialize_by_alias=True,
        # a response always has every field, so the schema, and the TypeScript types generated
        # from it, mark the fields that have defaults as required too.
        json_schema_serialization_defaults_required=True,
    )

    def to_json(self) -> SmarterDictType:
        """The model as the api returns it."""
        return self.model_dump(mode="json")


# ------------------------------------------------------------------------------
# installed extensions
# ------------------------------------------------------------------------------
class ExtensionSummary(ExtensionConsoleModel):
    """An installed extension, as the Extensions list shows it."""

    id: int
    slug: str = Field(..., description="The extension's slug, e.g. weather.")
    display_name: str
    description: str
    publisher: str = Field(..., description="The publisher's registry id, or an uploaded archive's authors.")
    source: Source
    trust_badge: TrustBadge
    trust_badge_label: str = Field(..., description="The badge, as people read it, e.g. Official Smarter Extension.")
    enabled: bool
    installed_version: Optional[str] = None
    latest_version: Optional[str] = Field(None, description="The newest compatible version in the registry.")
    update_available: bool
    latest_checked_at: Optional[datetime] = None
    error: str = Field("", description="The last error from loading the extension or running its lifecycle hooks.")
    detail_url: str = Field(..., description="The url of the extension's detail page.")

    @classmethod
    def from_model(cls, extension: "Extension", detail_url: str) -> "ExtensionSummary":
        """
        The summary of an installed extension.

        :param extension: The extension, with its installed version.
        :param detail_url: The url of its detail page.
        """
        return cls(
            id=extension.pk,
            slug=extension.slug,
            display_name=extension.display_name,
            description=extension.description,
            publisher=extension.publisher,
            source=extension.source,  # type: ignore[arg-type]
            trust_badge=extension.trust_badge,  # type: ignore[arg-type]
            trust_badge_label=TRUST_BADGE_LABELS.get(extension.trust_badge, extension.trust_badge),
            enabled=extension.enabled,
            installed_version=extension.installed_version.version if extension.installed_version else None,
            latest_version=extension.latest_version or None,
            update_available=extension.update_available,
            latest_checked_at=extension.latest_checked_at,
            error=extension.error,
            detail_url=detail_url,
        )


class ExtensionListResponse(ExtensionConsoleModel):
    """The Extensions list: the installed extensions, and the state of the registry."""

    objects: list[ExtensionSummary]
    registry_enabled: bool = Field(..., description="Whether the registry's public key is configured.")
    updates_available: int = Field(..., description="How many installed extensions have an update in the registry.")


class ExtensionTool(ExtensionConsoleModel):
    """One of an extension's tools, as the LLM sees it."""

    name: str = Field(..., description="The tool's name in the extension, e.g. get_weather.")
    function_name: str = Field(..., description="The name the LLM sees, e.g. ext_weather_get_weather.")
    description: str
    parameters: JsonValue = Field(..., description="The JSON Schema of the tool's arguments.")


class ExtensionSetting(ExtensionConsoleModel):
    """One of an extension's settings: its declaration, and its configured value."""

    name: str
    type: SettingType
    description: str
    required: bool
    default: Optional[SettingValue] = None
    choices: Optional[list[str]] = None
    value: Optional[SettingValue] = Field(None, description="The configured value. Always null for a secret setting.")
    secret_id: Optional[int] = Field(None, description="The id of a secret setting's Secret.")
    secret_name: Optional[str] = Field(None, description="The name of a secret setting's Secret.")
    is_set: bool = Field(..., description="Whether the setting has a configured value, or a Secret.")


class ExtensionVersionInfo(ExtensionConsoleModel):
    """One installed version of an extension."""

    id: int
    version: str
    sha256: str
    source_url: str
    installed_by: Optional[str] = Field(None, description="The username of the superuser who installed it.")
    created_at: Optional[datetime] = None
    is_installed: bool = Field(..., description="Whether it is the version that runs.")


class ExtensionResource(ExtensionConsoleModel):
    """A SAM resource that an extension created."""

    kind: str
    name: str
    owner: str = Field(..., description="The username of the resource's owner.")
    version: str = Field(..., description="The extension version that created or last applied it.")
    managed: bool = Field(..., description="Whether it came from the package's manifests/ directory.")


class ExtensionSwitch(ExtensionConsoleModel):
    """A waffle switch that an extension owns."""

    name: str = Field(..., description="The switch's full name, e.g. ext_weather_verbose.")
    description: str
    active: bool


class AccountRef(ExtensionConsoleModel):
    """An account, for the extension's availability."""

    id: int
    account_number: str
    company_name: str

    @classmethod
    def from_model(cls, account: "Account") -> "AccountRef":
        """The reference to an account."""
        return cls(id=account.pk, account_number=account.account_number, company_name=account.company_name or "")


class SecretRef(ExtensionConsoleModel):
    """A Secret of the platform's admin, which a secret setting can use."""

    id: int
    name: str

    @classmethod
    def from_model(cls, secret: "Secret") -> "SecretRef":
        """The reference to a Secret."""
        return cls(id=secret.pk, name=secret.name)


class ExtensionDetail(ExtensionSummary):
    """An installed extension, as its detail page shows it."""

    homepage: Optional[str] = None
    license: Optional[str] = None
    docs_html: str = Field("", description="The extension's documentation, as HTML rendered safely.")
    tools: list[ExtensionTool]
    load_error: Optional[str] = Field(None, description="Why the extension's code does not load, if it does not.")
    settings: list[ExtensionSetting]
    missing_settings: list[str] = Field(..., description="Required settings that block enabling the extension.")
    versions: list[ExtensionVersionInfo]
    resources: list[ExtensionResource]
    switches: list[ExtensionSwitch]
    all_accounts: bool
    accounts: list[AccountRef] = Field(..., description="The accounts that may use it, when not all accounts may.")
    available_secrets: list[SecretRef] = Field(..., description="The platform admin's Secrets, for secret settings.")


class ExtensionDetailResponse(ExtensionConsoleModel):
    """An extension's detail page."""

    extension: ExtensionDetail


# ------------------------------------------------------------------------------
# the registry
# ------------------------------------------------------------------------------
class RegistryVersionInfo(ExtensionConsoleModel):
    """A released version of a registry extension."""

    version: str
    requires_smarter: Optional[str] = None
    released_at: Optional[datetime] = None
    compatible: bool = Field(..., description="Whether it works with this platform's Smarter version.")


class RegistryExtension(ExtensionConsoleModel):
    """An extension in the registry, as the Browse tab shows it."""

    slug: str
    display_name: str
    description: str
    publisher: str = Field(..., description="The publisher's name.")
    publisher_url: Optional[str] = None
    trust_badge: TrustBadge
    trust_badge_label: str
    homepage: Optional[str] = None
    license: Optional[str] = None
    docs_html: str = Field("", description="The extension's documentation, as HTML rendered safely.")
    latest_version: Optional[str] = Field(None, description="The newest version compatible with this platform.")
    versions: list[RegistryVersionInfo] = Field(..., description="Every released version, newest first.")
    installed_version: Optional[str] = None
    action: RegistryAction
    detail_url: Optional[str] = Field(None, description="The installed extension's detail page, if it is installed.")


class RegistryResponse(ExtensionConsoleModel):
    """The registry's extensions, or why they cannot be listed."""

    enabled: bool = Field(..., description="Whether the registry's public key is configured.")
    error: Optional[str] = Field(None, description="Why the registry cannot be read, if it cannot.")
    objects: list[RegistryExtension]


# ------------------------------------------------------------------------------
# requests and their responses
# ------------------------------------------------------------------------------
class RegistryRequest(ExtensionConsoleModel):
    """A request for the registry's extensions."""

    refresh: bool = Field(False, description="Whether to download the index again, rather than read the cache.")


class InstallRequest(ExtensionConsoleModel):
    """A request to install, or update, an extension from the registry."""

    slug: str
    version: Optional[str] = Field(None, description="The version; the newest compatible version if null.")


class RollbackRequest(ExtensionConsoleModel):
    """A request to make an earlier version the one that runs."""

    version_id: int


class SecretInput(ExtensionConsoleModel):
    """The new value of a secret setting: an existing Secret, a value to save in a new one, or neither, to clear it."""

    secret_id: Optional[int] = Field(None, description="One of the platform admin's Secrets.")
    value: Optional[str] = Field(None, description="A value, saved in the Secret extension_<slug>_<setting>.")


class ConfigureRequest(ExtensionConsoleModel):
    """A request to change some of an extension's settings.

    Settings that are left out don't change.
    """

    values: dict[str, Optional[SettingValue]] = Field(
        default_factory=dict, description="Non-secret settings' values, by name; null resets one to its default."
    )
    secrets: dict[str, SecretInput] = Field(default_factory=dict, description="Secret settings' values, by name.")


class AvailabilityRequest(ExtensionConsoleModel):
    """A request to change which accounts may use an extension."""

    all_accounts: bool
    account_ids: list[int] = Field(default_factory=list)


class ActionResponse(ExtensionConsoleModel):
    """The result of an action: what happened, and the extension as it now is, if it still exists."""

    message: str
    extension: Optional[ExtensionDetail] = None


class AccountsResponse(ExtensionConsoleModel):
    """Every account, for the availability picker."""

    objects: list[AccountRef]


class ErrorResponse(ExtensionConsoleModel):
    """Why a request failed."""

    error: str


RESPONSE_MODELS: tuple[type[BaseModel], ...] = (
    ExtensionListResponse,
    ExtensionDetailResponse,
    RegistryResponse,
    ActionResponse,
    AccountsResponse,
    ErrorResponse,
)
"""The api's responses, whose schemas describe what the api sends: every field, always."""

REQUEST_MODELS: tuple[type[BaseModel], ...] = (
    RegistryRequest,
    InstallRequest,
    RollbackRequest,
    ConfigureRequest,
    AvailabilityRequest,
)
"""The api's requests, whose schemas describe what the api accepts: fields with defaults may be left out."""

CONTRACT_MODELS: tuple[type[BaseModel], ...] = RESPONSE_MODELS + REQUEST_MODELS
"""The models whose JSON Schemas the contract's schema has.

Their dependencies are included with them.
"""


# ------------------------------------------------------------------------------
# builders
# ------------------------------------------------------------------------------
def setting_states(extension: "Extension") -> list[ExtensionSetting]:
    """
    Return the declared settings of an extension's installed version, with their configured values.

    :param extension: The extension, with an installed version.
    """
    if extension.installed_version is None:
        return []
    rows = {row.name: row for row in extension.settings.select_related("secret").all()}  # type: ignore[attr-defined]
    states = []
    for spec in extension.installed_version.parsed_manifest.smarter.settings:
        row = rows.get(spec.name)
        secret = row.secret if row is not None else None
        value: Union[SettingValue, None] = None
        if spec.type != ExtensionSettingType.SECRET and row is not None and row.value != "":
            try:
                value = spec.coerce(row.value)
            except ValueError:
                value = row.value
        states.append(
            ExtensionSetting(
                name=spec.name,
                type=spec.type.value,  # type: ignore[arg-type]
                description=spec.description,
                required=spec.required,
                default=spec.default,
                choices=spec.choices,
                value=value,
                secret_id=secret.pk if secret is not None else None,
                secret_name=secret.name if secret is not None else None,
                is_set=secret is not None if spec.type == ExtensionSettingType.SECRET else value is not None,
            )
        )
    return states


def version_infos(extension: "Extension", versions: list["ExtensionVersion"]) -> list[ExtensionVersionInfo]:
    """Return an extension's installed versions, newest first."""
    return [
        ExtensionVersionInfo(
            id=version.pk,
            version=version.version,
            sha256=version.sha256,
            source_url=version.source_url,
            installed_by=version.installed_by.username if version.installed_by else None,
            created_at=version.created_at,
            is_installed=version.pk == extension.installed_version_id,  # type: ignore[attr-defined]
        )
        for version in versions
    ]


def contract_schema() -> SmarterDictType:
    """The contract's JSON Schema (draft 2020-12): one definition, in ``$defs``, per model."""
    _, schema = models_json_schema(
        [(model, "serialization") for model in RESPONSE_MODELS] + [(model, "validation") for model in REQUEST_MODELS],
        title="Smarter Extension console api contract",
        description=(
            "The requests and responses of the web console's Extensions pages. Generated from "
            "smarter.apps.llmtool.extension.contract; do not edit."
        ),
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def contract_schema_json() -> str:
    """The contract's JSON Schema, as the text of ``extension-console.schema.json``."""
    return json.dumps(contract_schema(), indent=2, sort_keys=True) + "\n"


__all__ = [
    "AccountRef",
    "AccountsResponse",
    "ActionResponse",
    "AvailabilityRequest",
    "CONTRACT_MODELS",
    "REQUEST_MODELS",
    "RESPONSE_MODELS",
    "ConfigureRequest",
    "ErrorResponse",
    "ExtensionConsoleModel",
    "ExtensionDetail",
    "ExtensionDetailResponse",
    "ExtensionListResponse",
    "ExtensionResource",
    "ExtensionSetting",
    "ExtensionSummary",
    "ExtensionSwitch",
    "ExtensionTool",
    "ExtensionVersionInfo",
    "InstallRequest",
    "RegistryExtension",
    "RegistryRequest",
    "RegistryResponse",
    "RegistryVersionInfo",
    "RollbackRequest",
    "SCHEMA_PATH",
    "SecretInput",
    "SecretRef",
    "contract_schema",
    "contract_schema_json",
    "setting_states",
    "version_infos",
]
