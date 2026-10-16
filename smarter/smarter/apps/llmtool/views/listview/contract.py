"""
The contract of the LLMTool list's Extensions tab: the JSON of its api, as Pydantic models.

The LLMTool list, a React app (``@smarter/llmtool-list``), has a read-only Extensions tab that
lists the installed Extensions that the user's account may use. Its api,
:class:`~smarter.apps.llmtool.views.listview.api.PluginListApiExtensionsView`, builds every
response from these models. The JSON is camelCase.

``manage.py export_extension_list_schema`` writes the models' JSON Schema to
``extension-list.schema.json``, beside this module, from which ``@smarter/llmtool-list``
generates its TypeScript types (``make llmtool-list-contract``). A test fails if the committed
schema is out of date.

Every user may see the extensions that their account may use, but only superusers manage them,
in the Extensions console, whose own contract is :mod:`smarter.apps.llmtool.extension.contract`.
So these models have nothing that only an administrator needs: no settings, errors, registry
updates or links to the console.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field, ValidationError
from pydantic.alias_generators import to_camel
from pydantic.json_schema import models_json_schema

from smarter.apps.llmtool.extension.contract import (
    TRUST_BADGE_LABELS,
    Source,
    TrustBadge,
)
from smarter.common.const import SMARTER_PROJECT_WEBSITE_URL
from smarter.lib.django.pagination import ListViewPagination
from smarter.lib.typing import SmarterDictType

if TYPE_CHECKING:
    from smarter.apps.llmtool.models import Extension

SCHEMA_PATH = Path(__file__).parent / "extension-list.schema.json"
"""The committed JSON Schema of the contract."""
SCHEMA_ID = f"{SMARTER_PROJECT_WEBSITE_URL}/schemas/extension-list.schema.json"


class ExtensionListModel(BaseModel):
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


class ExtensionListItem(ExtensionListModel):
    """An installed Extension, as the read-only Extensions tab of the LLMTool list shows it."""

    id: int
    slug: str = Field(..., description="The extension's slug, e.g. weather. An LLMClient manifest lists it by slug.")
    display_name: str
    description: str
    publisher: str = Field(..., description="The publisher's registry id, or an uploaded archive's authors.")
    source: Source
    trust_badge: TrustBadge
    trust_badge_label: str = Field(..., description="The badge, as people read it, e.g. Official Smarter Extension.")
    enabled: bool = Field(..., description="Whether the extension's tools are offered to LLMs.")
    version: Optional[str] = Field(None, description="The installed version.")
    license: Optional[str] = Field(None, description="The license, from the installed version's manifest.")
    homepage: Optional[str] = Field(None, description="The homepage, from the installed version's manifest.")
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_model(cls, extension: "Extension") -> "ExtensionListItem":
        """
        The list item of an installed extension.

        :param extension: The extension, with its installed version.
        :returns: The extension's list item.
        """
        version = extension.installed_version
        license_name: Optional[str] = None
        homepage: Optional[str] = None
        if version is not None:
            try:
                project = version.parsed_manifest.project
                license_name = project.license
                homepage = project.urls.get("Homepage")
            except ValidationError:
                # parsed_manifest() logs the invalid manifest. The list still shows the extension.
                pass
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
            version=version.version if version else None,
            license=license_name,
            homepage=homepage,
            created_at=extension.created_at,
            updated_at=extension.updated_at,
        )


class ExtensionListPage(ExtensionListModel):
    """A page of the Extensions tab: the extensions, and the description of the page."""

    objects: list[ExtensionListItem]
    pagination: ListViewPagination


RESPONSE_MODELS: tuple[type[BaseModel], ...] = (ExtensionListPage,)
"""The api's responses, whose schemas describe what the api sends.

Their dependencies are included with them.
"""


def contract_schema() -> SmarterDictType:
    """The contract's JSON Schema (draft 2020-12): one definition, in ``$defs``, per model."""
    _, schema = models_json_schema(
        [(model, "serialization") for model in RESPONSE_MODELS],
        title="Smarter LLMTool list Extensions api contract",
        description=(
            "The responses of the read-only Extensions tab of the web console's LLMTool list. Generated from "
            "smarter.apps.llmtool.views.listview.contract; do not edit."
        ),
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def contract_schema_json() -> str:
    """The contract's JSON Schema, as the text of ``extension-list.schema.json``."""
    return json.dumps(contract_schema(), indent=2, sort_keys=True) + "\n"


__all__ = [
    "RESPONSE_MODELS",
    "SCHEMA_ID",
    "SCHEMA_PATH",
    "ExtensionListItem",
    "ExtensionListModel",
    "ExtensionListPage",
    "contract_schema",
    "contract_schema_json",
]
