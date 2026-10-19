"""
The contract of an LLMClient's deployment page: the JSON that its React app renders, as Pydantic models.

The ``@smarter/llmclient-deployment`` React package renders the page in two places:

- **public**: the page at a deployed LLMClient's url, which anyone can open,
  :class:`~smarter.apps.llmclient.views.endpoints.LLMClientEndpointsView`, which puts the page's data in
  the page with Django's ``json_script``, so that the app renders without a request of its own;
- **workbench**: the "Deployment" tab of the Prompt Engineer's Workbench's Console, which renders the
  package's component, and fetches the page's data from
  :class:`~smarter.apps.prompt.views.detailviews.prompt_deployment_view.LLMClientDeploymentView` when the
  tab is first opened. It adds the LLMClient's owner and its api keys, and manages them in place.

Both views build a :class:`LLMClientDeploymentPage`. The workbench's api key actions are POSTs that answer
with an :class:`ApiKeyActionResponse`, the page as it now is, or an :class:`ErrorResponse`. The JSON is
camelCase.

``manage.py export_llmclient_deployment_schema`` writes the models' JSON Schema to
``llmclient-deployment.schema.json``, beside this module, from which ``@smarter/llmclient-deployment``
generates its TypeScript types (``make llmclient-deployment-contract``). A test fails if the committed
schema is out of date.

The public page names no owner and has no api keys: :meth:`LLMClientDeploymentPage.public` leaves them out.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.json_schema import JsonSchemaMode, models_json_schema

from smarter.common.const import SMARTER_PROJECT_WEBSITE_URL
from smarter.lib.typing import SmarterDictType

SCHEMA_PATH = Path(__file__).parent / "llmclient-deployment.schema.json"
"""The committed JSON Schema of the contract."""
SCHEMA_ID = f"{SMARTER_PROJECT_WEBSITE_URL}/schemas/llmclient-deployment.schema.json"

PageMode = Literal["public", "workbench"]
"""Where the page is: at the deployed LLMClient's url, or in the workbench's "Deployment" tab."""

ErrorCode = Literal[
    "not_found",
    "invalid_request",
    "not_owner",
    "not_admin",
    "not_account_admin",
    "invalid_name",
    "duplicate_name",
    "api_key_not_found",
]
"""Why an api key action failed, which the React app explains in the user's language."""


class LLMClientDeploymentModel(BaseModel):
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
        """The model as the page and the api send it."""
        return self.model_dump(mode="json")


# ------------------------------------------------------------------------------
# the page
# ------------------------------------------------------------------------------
class DeploymentLLMClient(LLMClientDeploymentModel):
    """The LLMClient, as the page describes it."""

    name: str
    app_name: str = Field(..., description="The chat's title, or the LLMClient's name if it has none.")
    example_prompts: list[str]
    provider: Optional[str] = None
    model: Optional[str] = None
    version: Optional[str] = None
    url: str = Field(
        ...,
        description="Its url, without a trailing slash: the url that it will have, if it isn't deployed.",
    )
    workbench_url: str = Field(..., description="The url of its Prompt Engineer's Workbench.")


class DeploymentSnippets(LLMClientDeploymentModel):
    """The commands, manifest excerpts and code that the page shows, each in a terminal with a Copy button."""

    deploy_command: str = Field(..., description="The command that deploys the LLMClient.")
    deploy_commands: str = Field(..., description="The commands that apply its manifest, and deploy it.")
    config_command: str = Field(..., description="The curl command that POSTs to its /config/ endpoint.")
    prompt_command: str = Field(..., description="The curl command that POSTs a prompt to its /prompt/ endpoint.")
    session_config_command: str = Field(
        ..., description="The curl command that continues a chat session: its /config/ request, with the session's key."
    )
    session_prompt_command: str = Field(
        ..., description="The curl command that sends a prompt in a chat session, with the session's key."
    )
    example_response: str = Field(..., description="An abbreviated /prompt/ response, as indented JSON.")
    allowed_origins_yaml: str
    api_key_yaml: str
    drupal_install_commands: str
    npm_install_command: str
    embed_html: str
    embed_html_with_api_key: str
    react_snippet: str
    react_snippet_with_api_key: str
    create_api_key_command: str
    switch_command: str = Field(
        ..., description="The command that turns off the page at deployed LLMClients' urls, for administrators."
    )


class DeploymentLinks(LLMClientDeploymentModel):
    """The urls that the page links to, which depend on the platform's configuration."""

    api_keys_url: str = Field(..., description="The web console's API Keys page, absolute.")
    marketing_site_url: str
    docs_url: str
    logo_url: str
    product_name: str
    product_description: str


class DeploymentOwnership(LLMClientDeploymentModel):
    """Who owns the LLMClient, and how a user who may not change it can clone it.

    Workbench only.
    """

    owner: str = Field(..., description="The owner's full name and username, or the username.")
    can_edit: bool = Field(..., description="Whether the user may change the LLMClient: ownership permission.")
    llmclient_list_url: str = Field(..., description="The url of the LLM Clients list, where it can be cloned.")
    ownership_docs_url: str


class DeploymentApiKey(LLMClientDeploymentModel):
    """One of the account's api keys that the user may manage."""

    key_id: UUID
    name: str
    description: str
    is_active: bool
    owner: str = Field(..., description="The username of the key's owner.")
    last_used_at: Optional[datetime] = None
    is_attached: bool = Field(..., description="Whether it is the LLMClient's api key.")


class DeploymentAttachedApiKey(LLMClientDeploymentModel):
    """The LLMClient's api key, which every request to its url needs, while it is active."""

    name: str
    is_active: bool


class DeploymentApiKeys(LLMClientDeploymentModel):
    """The LLMClient's api key, the account's api keys, what the user may do, and where.

    Workbench only.
    """

    api_keys: list[DeploymentApiKey] = Field(..., description="Newest first.")
    attached: Optional[DeploymentAttachedApiKey] = None
    can_manage: bool = Field(..., description="Whether the user may attach and detach api keys: ownership.")
    can_create: bool = Field(..., description="Whether the user may create an api key: staff.")
    create_url: str
    attach_url: str
    detach_url: str


class LLMClientDeploymentPage(LLMClientDeploymentModel):
    """Everything that the page shows."""

    mode: PageMode
    llmclient: DeploymentLLMClient
    deployed: bool
    authenticated: bool = Field(..., description="Whether its url requires an api key.")
    manifest_yaml: Optional[str] = Field(
        None, description="Its manifest, without its owner's username, or null if it couldn't be built."
    )
    snippets: DeploymentSnippets
    links: DeploymentLinks
    ownership: Optional[DeploymentOwnership] = None
    api_keys: Optional[DeploymentApiKeys] = None

    def public(self) -> "LLMClientDeploymentPage":
        """
        The page at the deployed LLMClient's url, which anyone can open: without its owner or api keys.

        :returns: A copy of the page.
        :rtype: LLMClientDeploymentPage
        """
        return self.model_copy(update={"mode": "public", "ownership": None, "api_keys": None})


# ------------------------------------------------------------------------------
# the workbench's api key actions
# ------------------------------------------------------------------------------
class CreateApiKeyRequest(LLMClientDeploymentModel):
    """Create an api key for the user, and attach it to the LLMClient if asked to."""

    name: str = Field(..., description="The key's name, in snake_case.")
    description: str = ""
    attach: bool = False


class AttachApiKeyRequest(LLMClientDeploymentModel):
    """Attach one of the account's api keys to the LLMClient, in place of any other."""

    key_id: UUID


class NewApiKey(LLMClientDeploymentModel):
    """An api key that was just created.

    Its secret is in this response only.
    """

    name: str
    secret: str


class ApiKeyActionResponse(LLMClientDeploymentModel):
    """The page after an api key action, and a new key's secret."""

    page: LLMClientDeploymentPage
    new_api_key: Optional[NewApiKey] = None


class ErrorResponse(LLMClientDeploymentModel):
    """Why an api key action failed: its code, and an English message for logs and developers."""

    error: str
    code: ErrorCode


RESPONSE_MODELS: tuple[type[BaseModel], ...] = (LLMClientDeploymentPage, ApiKeyActionResponse, ErrorResponse)
"""What the views send: every field, always."""

REQUEST_MODELS: tuple[type[BaseModel], ...] = (CreateApiKeyRequest, AttachApiKeyRequest)
"""What the api accepts: fields with defaults may be left out."""


def contract_schema() -> SmarterDictType:
    """The contract's JSON Schema (draft 2020-12): one definition, in ``$defs``, per model."""
    # what the views send is the models' serialization, and what the api accepts, their validation.
    responses: list[tuple[type[BaseModel], JsonSchemaMode]] = [(model, "serialization") for model in RESPONSE_MODELS]
    requests: list[tuple[type[BaseModel], JsonSchemaMode]] = [(model, "validation") for model in REQUEST_MODELS]
    _, schema = models_json_schema(
        responses + requests,
        title="Smarter LLMClient deployment page contract",
        description=(
            "The data of an LLMClient's deployment page, and of its api key actions. Generated from "
            "smarter.apps.llmclient.views.deployment_contract; do not edit."
        ),
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def contract_schema_json() -> str:
    """The contract's JSON Schema, as the text of ``llmclient-deployment.schema.json``."""
    return json.dumps(contract_schema(), indent=2, sort_keys=True) + "\n"


__all__ = [
    "REQUEST_MODELS",
    "RESPONSE_MODELS",
    "SCHEMA_ID",
    "SCHEMA_PATH",
    "ApiKeyActionResponse",
    "AttachApiKeyRequest",
    "CreateApiKeyRequest",
    "DeploymentApiKey",
    "DeploymentApiKeys",
    "DeploymentAttachedApiKey",
    "DeploymentLLMClient",
    "DeploymentLinks",
    "DeploymentOwnership",
    "DeploymentSnippets",
    "ErrorCode",
    "ErrorResponse",
    "LLMClientDeploymentModel",
    "LLMClientDeploymentPage",
    "PageMode",
    "contract_schema",
    "contract_schema_json",
]
