"""
The contract of the web console's session api, ``GET /api/web/session/``, as Pydantic models.

The single-page console (:doc:`ADR-035 </adr/035-single-page-app>`) calls it when it starts, and again
after the user signs in, signs out or changes profile. It replaces what Django's context processors and
the React apps' template tags put into each server-rendered page: who the user is, the account that the
console acts for, the platform's branding, which sign-in options and features are on, the languages, the SAM kinds,
and the state of the welcome dialog and onboarding hints. The JSON is camelCase.

A request without a signed-in user gets a :class:`ConsoleSession` whose ``user``, ``account``,
``onboarding``, ``welcome``, ``badges`` and ``sidebar`` are ``null``: what the sign-in pages need, and nothing about
any user.

``manage.py export_console_session_schema`` writes the models' JSON Schema to
``console-session.schema.json``, beside this module, from which ``@smarter/console`` generates its
TypeScript types (``make console-session-contract``). A test fails if the committed schema is out of date.
"""

import json
from pathlib import Path
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field
from pydantic.alias_generators import to_camel
from pydantic.json_schema import models_json_schema

from smarter.common.const import SMARTER_PROJECT_WEBSITE_URL
from smarter.lib.typing import SmarterDictType

SCHEMA_PATH = Path(__file__).parent / "console-session.schema.json"
"""The committed JSON Schema of the contract."""
SCHEMA_ID = f"{SMARTER_PROJECT_WEBSITE_URL}/schemas/console-session.schema.json"


class ConsoleSessionModel(BaseModel):
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
        """The model as the view sends it."""
        return self.model_dump(mode="json")


class ConsoleBranding(ConsoleSessionModel):
    """The platform's identity and contacts, which the console shows in its header, footer and sign-in pages."""

    product_name: str = Field(..., description="The product's name, e.g. The Smarter Project.")
    product_description: str = Field(..., description="A one-sentence description of the product.")
    corporate_name: str = Field(..., description="The organization that runs this platform.")
    corporate_address: str = Field(..., description="Its postal address, on one line, or empty.")
    support_email: str = Field(..., description="The support email address, or empty.")
    support_phone_number: str = Field(..., description="The support phone number, or empty.")
    support_hours: str = Field(..., description="When support answers, or empty.")
    primary_contact: str = Field(..., description="The name of the platform's primary contact, or empty.")
    contact_url: str = Field(..., description="A page for contacting the organization.")
    copyright: str = Field(..., description="The copyright notice of the footer.")
    url_facebook: str = Field(..., description="The organization's Facebook page, or empty.")
    url_twitter: str = Field(..., description="The organization's X/Twitter page, or empty.")
    url_linkedin: str = Field(..., description="The organization's LinkedIn page, or empty.")
    url_slack: str = Field(..., description="An invitation to the project's Slack workspace, or empty.")
    logo_url: str = Field(..., description="The logo, an absolute url on the project's CDN.")
    marketing_site_url: str = Field(..., description="The organization's website.")
    project_website_url: str = Field(..., description="The Smarter project's website.")
    project_docs_url: str = Field(..., description="The documentation, docs.smarter.sh.")
    legal_url: str = Field(..., description="The legal page: terms, privacy and cookies.")
    environment_url: str = Field(..., description="This platform's own url, e.g. https://platform.example.com.")


class ConsoleSignIn(ConsoleSessionModel):
    """The ways to sign in or sign up that the sign-in pages offer."""

    google: bool = Field(..., description="Whether the Sign in with Google button shows.")
    github: bool = Field(..., description="Whether the Sign in with GitHub button shows.")
    sign_up: bool = Field(..., description="Whether anyone may create an account: the sign-up page answers 404 if not.")
    footer_links: bool = Field(..., description="Whether the sign-in page shows its footer's links.")
    doodle: bool = Field(..., description="Whether the sign-in pages show the doodle of the day.")


class ConsoleLanguageOption(ConsoleSessionModel):
    """A language that the console is translated into."""

    code: str = Field(..., description="Its code, e.g. pt-br.")
    name: str = Field(..., description="Its name, in itself, e.g. Português Brasileiro.")


class ConsoleLanguage(ConsoleSessionModel):
    """The console's languages, and the one that this response, and the session, are in."""

    current: str = Field(..., description="The code of the session's language.")
    bidi: bool = Field(..., description="Whether the session's language is written right to left.")
    languages: list[ConsoleLanguageOption] = Field(..., description="Every language the menu offers.")


class ConsoleCookies(ConsoleSessionModel):
    """The names and domain of Django's cookies, which the console's api calls send."""

    csrf_cookie_name: str = Field(..., description="The CSRF cookie, whose value is sent as X-CSRFToken.")
    session_cookie_name: str = Field(..., description="The session cookie.")
    cookie_domain: str = Field(..., description="The cookies' domain, or empty for the request's host.")


class ConsoleFlags(ConsoleSessionModel):
    """The console's optional features: which pages exist, and which tabs and widgets show."""

    proxy: bool = Field(..., description="Whether the Proxies pages exist.")
    vectorstore: bool = Field(..., description="Whether the Vectorstores pages exist.")
    manifest_drop_zone: bool = Field(..., description="Whether the manifest drop zone page exists.")
    terminal: bool = Field(..., description="Whether the Terminal page exists for this user, a superuser.")
    passthrough: bool = Field(..., description="Whether the Prompt Passthrough page exists.")
    server_logs: bool = Field(..., description="Whether the Server Logs tabs show.")
    did_you_know: bool = Field(..., description="Whether the header shows a Did you know? tip.")
    react_debug_mode: bool = Field(..., description="Whether the React apps log their debugging output.")


class ConsoleUser(ConsoleSessionModel):
    """The signed-in user."""

    username: str
    email: str
    first_name: str
    last_name: str
    is_superuser: bool
    is_staff: bool
    profile_image_url: str = Field(..., description="The user's avatar, or the default image.")
    user_profile_count: int = Field(..., description="How many accounts the user belongs to.")


class ConsoleAccount(ConsoleSessionModel):
    """The account that the console acts for: that of the user's selected profile."""

    account_number: str = Field(..., description="The account's number, e.g. 3141-5926-5359.")
    name: str = Field(..., description="The account's company name.")


class ConsoleOnboarding(ConsoleSessionModel):
    """The state of the console's onboarding hints for the user."""

    enabled: bool = Field(..., description="Whether hints show by themselves.")
    seen: list[str] = Field(..., description="The hints that the user has seen, which no longer show by themselves.")


class ConsoleWelcome(ConsoleSessionModel):
    """The state of the welcome dialog for the user."""

    show_at_startup: bool = Field(..., description="Whether the dialog opens by itself each time the user signs in.")
    show: bool = Field(
        ..., description="Whether it opens by itself now: it shows at startup, and hasn't been closed in this session."
    )


class ConsoleBadges(ConsoleSessionModel):
    """The counts that the sidebar shows beside its items."""

    extension_updates: int = Field(
        ..., description="Installed extensions with an update; 0 for a user who isn't a superuser."
    )


class ConsoleSidebar(ConsoleSessionModel):
    """
    The urls of the sidebar's links, reversed by the backend.

    A link that the platform or the user doesn't have is null, and the sidebar leaves it out.
    """

    dashboard: str = Field(..., description="The dashboard.")
    prompt_passthrough: Optional[str] = Field(..., description="The Prompt Passthrough, while it is enabled.")
    manifest_drop_zone: Optional[str] = Field(..., description="The manifest drop zone, while it is enabled.")
    terminal: Optional[str] = Field(..., description="The Terminal, for a superuser, while it is enabled.")
    providers: str = Field(..., description="The Providers list.")
    proxies: Optional[str] = Field(..., description="The Proxies list, while proxies are enabled.")
    llmhost: str = Field(..., description="The LLM Hosts list.")
    llmhostcompute: str = Field(..., description="The LLM Host Compute list.")
    workbench: str = Field(..., description="The LLMClients list, the Prompt Engineer's Workbench.")
    orchestrators: str = Field(..., description="The Orchestrators list.")
    api_keys: str = Field(..., description="The API Keys list.")
    custom_domains: str = Field(..., description="The Custom Domains list.")
    extensions: str = Field(..., description="The Extensions console.")
    plugins: str = Field(..., description="The LLM Tools list.")
    mcpclients: str = Field(..., description="The MCP Clients list.")
    connections: str = Field(..., description="The Connections list.")
    vectorsearches: str = Field(..., description="The Vectorsearches list.")
    vectorstores: Optional[str] = Field(..., description="The Vectorstores list, while vectorstores are enabled.")
    budgets: str = Field(..., description="The Budgets list.")
    guardrails: str = Field(..., description="The Guardrails list.")
    secrets: str = Field(..., description="The Secrets list.")
    example_manifests: str = Field(..., description="The example manifests.")
    openapi: str = Field(..., description="The OpenAPI contract.")
    json_schemas: str = Field(..., description="The SAM JSON Schemas.")
    infrastructure_resources: Optional[str] = Field(
        ..., description="The Infrastructure Resources list, for a superuser."
    )
    admin: Optional[str] = Field(..., description="The Django admin, for a staff user.")


class ConsoleSession(ConsoleSessionModel):
    """Everything that the console needs to start, for the request's user, or for a visitor who isn't signed in."""

    is_authenticated: bool = Field(..., description="Whether the request has a signed-in user.")
    version: str = Field(..., description="The platform's version.")
    branding: ConsoleBranding
    sign_in: ConsoleSignIn
    language: ConsoleLanguage
    cookies: ConsoleCookies
    flags: ConsoleFlags
    sam_kinds: list[str] = Field(
        ...,
        description=(
            "Every SAM kind, sorted by name, e.g. LLMClient: the docs pages list each one's example manifest "
            "and JSON Schema."
        ),
    )
    user: Optional[ConsoleUser] = Field(..., description="The signed-in user, or null.")
    account: Optional[ConsoleAccount] = Field(..., description="The account the console acts for, or null.")
    onboarding: Optional[ConsoleOnboarding] = Field(..., description="The onboarding hints' state, or null.")
    welcome: Optional[ConsoleWelcome] = Field(..., description="The welcome dialog's state, or null.")
    badges: Optional[ConsoleBadges] = Field(..., description="The sidebar's counts, or null.")
    sidebar: Optional[ConsoleSidebar] = Field(..., description="The sidebar's links, or null.")


RESPONSE_MODELS: tuple[type[BaseModel], ...] = (ConsoleSession,)
"""What the view sends."""


def contract_schema() -> SmarterDictType:
    """
    The contract's JSON Schema (draft 2020-12): one definition, in ``$defs``, per model.

    It also has the models of the console's account api, :mod:`smarter.apps.account.api.web.contract`,
    so that the console generates every type it sends and receives from one schema.
    """
    # pylint: disable=import-outside-toplevel
    from smarter.apps.account.api.web import contract as account_contract

    models = []
    for model in RESPONSE_MODELS + account_contract.RESPONSE_MODELS:
        models.append((model, "serialization"))
    for model in account_contract.REQUEST_MODELS:
        models.append((model, "validation"))
    _, schema = models_json_schema(
        models,
        title="Smarter web console session contract",
        description=(
            "What the web console needs to start, from GET /api/web/session/: the user, the account, the "
            "platform's branding, its sign-in options, features and languages, and the state of the welcome "
            "dialog and onboarding hints; and the requests and responses of its account api, /api/web/account/. "
            "Generated from smarter.apps.api.web.session.contract and smarter.apps.account.api.web.contract; "
            "do not edit."
        ),
    )
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def contract_schema_json() -> str:
    """The contract's JSON Schema, as the text of ``console-session.schema.json``."""
    return json.dumps(contract_schema(), indent=2, sort_keys=True) + "\n"


__all__ = [
    "ConsoleAccount",
    "ConsoleBadges",
    "ConsoleBranding",
    "ConsoleCookies",
    "ConsoleFlags",
    "ConsoleLanguage",
    "ConsoleLanguageOption",
    "ConsoleOnboarding",
    "ConsoleSession",
    "ConsoleSessionModel",
    "ConsoleSidebar",
    "ConsoleSignIn",
    "ConsoleUser",
    "ConsoleWelcome",
    "RESPONSE_MODELS",
    "SCHEMA_ID",
    "SCHEMA_PATH",
    "contract_schema",
    "contract_schema_json",
]
