"""
Pydantic models of the Smarter Chat api contract.

They describe the requests and responses of the configuration and prompt apis, and the prompt's
progress events.

These models are the contract's single source of truth:

- version 2 responses are built from them, by :mod:`smarter.apps.prompt.contract.builders`,
- version 1 responses, which are built as before for older clients, are validated against them by
  the tests,
- the JSON Schema in ``chat-contract.schema.json`` is generated from them (``manage.py
  export_chat_contract_schema``), and Smarter Chat generates its TypeScript types from that schema,
  and validates its test fixtures against it.

No field is a bare ``list[Any]`` or ``dict[str, Any]``: lists are of named models, and a value
that is stored as arbitrary JSON, e.g. a tool's result, is a :data:`PromptChatApiJson`, which is
exactly JSON. The models of Django ORM rows (:class:`PromptChatApiOrmModel`) and of the session's
history have exactly their fields. The LLMClient, the messages, the meta data and the completion
allow extra fields, which the LLM providers and the Console use, and which Smarter Chat displays as
is. Adding a field is backward compatible. Removing or renaming one that is declared here is not.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field, JsonValue
from typing_extensions import deprecated

from .const import CHAT_CONTRACT_V2, PUBLIC_LLMCLIENT_FIELDS, PUBLIC_META_DATA_FIELDS

if TYPE_CHECKING:
    from smarter.apps.llmclient.models import (
        LLMClientFunctions,
        LLMClientPlugin,
        LLMClientRequests,
    )
    from smarter.apps.llmtool.models import PluginMeta, PluginSelectorHistory
    from smarter.apps.prompt.models import PromptPluginUsage, PromptToolCall

PromptChatApiJson = JsonValue
"""
A value that is stored, and returned, as arbitrary JSON: a string, number, boolean, null, or a.

list or object of them. It is used only where the value has no fixed shape, e.g. a tool's result.
"""

SESSION_KEY_PATTERN = r"^[a-fA-F0-9]{64}$"
"""The format of a chat session's key.

See ``SmarterValidator.VALID_SESSION_KEY``.
"""

PromptChatApiProgressEventType = Literal[
    "llm_request",
    "tool_requested",
    "tool_responded",
    "plugin_called",
    "mcp_tool_called",
    "mcp_tool_responded",
    "mcp_tool_failed",
]
"""The ``type`` of a progress event.

See :class:`smarter.apps.prompt.progress.PromptProgressEvents`.
"""

PromptChatApiPluginClass = Literal["api", "skill", "sql", "static", "websearch", "imagesearch"]
"""A plugin's class: the choices of ``PluginMeta.plugin_class``.

See ``PluginMeta.PLUGIN_CLASSES``.
"""

PromptChatApiFunctionName = Literal["get_current_weather", "date_calculator", "calculator"]
"""A built-in function's name: the choices of ``LLMClientFunctions.name``.

See ``LLMClientFunctions.CHOICES``.
"""


V1_DEPRECATION = (
    "Version 1 of the Smarter Chat api contract is deprecated: use version 2, the default. "
    "See smarter.apps.prompt.contract.const."
)
"""The message of the deprecation warnings of version 1 of the contract."""

LEGACY_KEY_RENAMES = (
    ("llmclient", "chatbot"),
    ("account_number", "accountNumber"),
    ("prompt_history", "chat_history"),
)
"""The key renames of version 1 of the configuration, for the versions of Smarter Chat that expect.

'chatbot' rather than 'llmclient'. Each applies to every key that contains it, at every depth.
"""


@deprecated(V1_DEPRECATION)
def legacy_key_names(value: PromptChatApiJson) -> PromptChatApiJson:
    """
    A value whose dict keys are renamed for version 1.

    See :data:`LEGACY_KEY_RENAMES`.

    :param value: A JSON value: a dict or a list is renamed, anything else is returned as is.
    :type value: PromptChatApiJson
    :returns: The value, with its keys renamed at every depth.
    :rtype: PromptChatApiJson
    """
    if isinstance(value, dict):
        renamed = {}
        for key, item in value.items():
            new_key = key
            if isinstance(key, str):
                for old, new in LEGACY_KEY_RENAMES:
                    new_key = new_key.replace(old, new)
            renamed[new_key] = legacy_key_names(item)
        return renamed
    if isinstance(value, list):
        return [legacy_key_names(item) for item in value]
    return value


class PromptChatApiModel(BaseModel):
    """Base class of the contract's models, which allow extra fields."""

    model_config = ConfigDict(extra="allow")


# ------------------------------------------------------------------------------
# common
# ------------------------------------------------------------------------------


class PromptChatApiTextPart(PromptChatApiModel):
    """A message's text part, in the format of the OpenAI chat completion api."""

    type: Literal["text"]
    text: str


class PromptChatApiImageUrl(PromptChatApiModel):
    """The image of an image part: an http(s) or base64 data url."""

    url: str
    detail: Optional[Literal["auto", "low", "high"]] = None


class PromptChatApiImagePart(PromptChatApiModel):
    """A message's image part."""

    type: Literal["image_url"]
    image_url: PromptChatApiImageUrl


class PromptChatApiInputAudio(PromptChatApiModel):
    """The audio of an audio part: base64 encoded."""

    data: str
    format: Literal["wav", "mp3"]


class PromptChatApiAudioPart(PromptChatApiModel):
    """A message's audio part."""

    type: Literal["input_audio"]
    input_audio: PromptChatApiInputAudio


class PromptChatApiFileRef(PromptChatApiModel):
    """The file of a file part: its base64 data, or the id of an uploaded file."""

    file_data: Optional[str] = None
    file_id: Optional[str] = None
    filename: Optional[str] = None


class PromptChatApiFilePart(PromptChatApiModel):
    """A message's file part."""

    type: Literal["file"]
    file: PromptChatApiFileRef


class PromptChatApiRefusalPart(PromptChatApiModel):
    """An assistant message's refusal part."""

    type: Literal["refusal"]
    refusal: str


PromptChatApiContentPart = Annotated[
    Union[
        PromptChatApiTextPart,
        PromptChatApiImagePart,
        PromptChatApiAudioPart,
        PromptChatApiFilePart,
        PromptChatApiRefusalPart,
    ],
    Field(discriminator="type"),
]
"""A part of a message whose content is a list of parts, by its ``type``."""


class PromptChatApiFunctionCall(PromptChatApiModel):
    """The function that an assistant message calls."""

    name: str
    arguments: str = Field(..., description="The function's arguments, as a JSON string.")


class PromptChatApiToolCall(PromptChatApiModel):
    """A tool call of an assistant message, in the format of the OpenAI chat completion api."""

    id: str
    type: Literal["function"] = "function"
    function: PromptChatApiFunctionCall


class PromptChatApiMessage(PromptChatApiModel):
    """
    A message, in the format of the OpenAI chat completion api.

    Smarter adds two roles, which are only displayed and never sent to an LLM: ``smarter``, a note
    about what the backend did, and ``smarter_error``, a failed prompt's error.
    """

    role: str = Field(..., description="system, assistant, user, tool, smarter or smarter_error.")
    content: Optional[Union[str, list[PromptChatApiContentPart]]] = Field(
        None, description="The message's text, or its parts. Null for an assistant message that only calls tools."
    )
    tool_calls: Optional[list[PromptChatApiToolCall]] = Field(None, description="An assistant message's tool calls.")
    tool_call_id: Optional[str] = Field(None, description="The tool call that a tool message answers.")
    name: Optional[str] = Field(None, description="The name of a tool message's function.")


class PromptChatApiJournalMetadata(PromptChatApiModel):
    """The journal's record of a request, which every journaled response carries."""

    command: Optional[str] = Field(None, description="The journal's command, e.g. prompt.")
    thing: Optional[str] = Field(None, description="The journal's thing, e.g. LLMClient.")


class PromptChatApiErrorBody(PromptChatApiModel):
    """The error of a failed request: the same shape for every error of the configuration and prompt apis."""

    errorClass: str = Field(..., description="The name of the error's class, e.g. NotFound or LLMProviderError.")
    description: str = Field(..., description="A human-readable description, which Smarter Chat displays.")
    status: int = Field(..., description="The http status.")


class PromptChatApiErrorResponse(PromptChatApiModel):
    """The body of an error response of the configuration or prompt apis, in both versions of the contract."""

    error: PromptChatApiErrorBody
    api: Optional[str] = None
    metadata: Optional[PromptChatApiJournalMetadata] = None


class PromptChatApiEnvelope(PromptChatApiModel):
    """The fields that every journaled response adds beside ``data``."""

    api: str = Field(..., description='The api version, e.g. "smarter.sh/v1".')
    metadata: PromptChatApiJournalMetadata = Field(
        default_factory=PromptChatApiJournalMetadata, description="The journal's command and thing."
    )


# ------------------------------------------------------------------------------
# the configuration api
# ------------------------------------------------------------------------------


class PromptChatApiStyleSection(PromptChatApiModel):
    """
    A section of the LLMClient's styles: the colors of one of chatscope's components.

    A section has only the settings that its component has, in the manifest's
    ``spec.config.styles``. See :mod:`smarter.apps.llmclient.manifest.models.llmclient.styles`.
    """

    background_color: Optional[str] = None
    color: Optional[str] = None
    border_color: Optional[str] = None
    info_color: Optional[str] = None
    link_color: Optional[str] = None
    editor_background_color: Optional[str] = None
    placeholder_color: Optional[str] = None


class PromptChatApiStyles(PromptChatApiModel):
    """
    The look of the LLMClient's chat: its manifest's ``spec.config.styles``, with snake_case keys.

    Smarter Chat applies it as css custom properties. Every setting is optional, and one that is
    left out keeps the chat's default.
    """

    app_logo_url: Optional[str] = None
    app_background_image_url: Optional[str] = None
    app_background_image_size: Optional[Literal["cover", "contain", "auto"]] = None
    assistant_avatar_url: Optional[str] = None
    user_avatar_url: Optional[str] = None
    font_family: Optional[str] = None
    google_font: Optional[str] = None
    font_size: Optional[str] = None
    border_radius: Optional[str] = None
    main_container: Optional[PromptChatApiStyleSection] = None
    conversation_header: Optional[PromptChatApiStyleSection] = None
    message_list: Optional[PromptChatApiStyleSection] = None
    incoming_message: Optional[PromptChatApiStyleSection] = None
    outgoing_message: Optional[PromptChatApiStyleSection] = None
    message_input: Optional[PromptChatApiStyleSection] = None
    buttons: Optional[PromptChatApiStyleSection] = None
    typing_indicator: Optional[PromptChatApiStyleSection] = None


class PromptChatApiLLMClientBase(PromptChatApiModel):
    """The LLMClient fields of the configuration that Smarter Chat reads."""

    id: int
    name: str
    version: Optional[str] = None
    deployed: Optional[bool] = None
    provider: Optional[str] = None
    default_model: Optional[str] = None
    default_system_role: Optional[str] = Field(None, description="The system prompt of a new chat session.")
    app_name: Optional[str] = None
    app_assistant: Optional[str] = None
    app_welcome_message: Optional[str] = None
    app_example_prompts: Optional[list[str]] = None
    app_placeholder: Optional[str] = None
    app_info_url: Optional[str] = None
    app_file_attachment: Optional[bool] = None
    styles: Optional[PromptChatApiStyles] = Field(
        None, description="The look of the chat: the manifest's spec.config.styles, with snake_case keys."
    )


class PromptChatApiLLMClient(PromptChatApiLLMClientBase):
    """The LLMClient, in version 2 of the configuration."""

    url_llmclient: str = Field(..., description="The url of the LLMClient's prompt api.")


@deprecated(V1_DEPRECATION)
class PromptChatApiChatbotV1(PromptChatApiLLMClientBase):
    """The LLMClient, in version 1 of the configuration, whose keys are renamed: llmclient becomes chatbot."""

    url_chatbot: str = Field(..., description="The url of the LLMClient's prompt api.")


class PromptChatApiOrmModel(BaseModel):
    """
    Base class of the contract's models of Django ORM rows.

    Their fields are exactly the rows' fields, so extra fields are forbidden. Each is built from its
    row by ``from_model()``.
    """

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="The row's primary key.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")


class PromptChatApiPluginMeta(PromptChatApiOrmModel):
    """
    A plugin's metadata: a :class:`smarter.apps.llmtool.models.PluginMeta`.

    Its owner is left out: the configuration never includes a user's profile.
    """

    name: str = Field(..., max_length=255, description="MetaDataModel.name, in snake_case.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, max_length=255, description="MetaDataModel.version, e.g. 1.0.0.")
    tags: list[str] = Field(default_factory=list, description="MetaDataModel.tags, by name.")
    annotations: Optional[Union[list[dict[str, PromptChatApiJson]], dict[str, PromptChatApiJson]]] = Field(
        None, description="MetaDataModel.annotations: a list of key-value pairs, or, in legacy rows, an object."
    )
    plugin_class: PromptChatApiPluginClass = Field(..., description="PluginMeta.plugin_class.")

    @classmethod
    def from_model(cls, plugin_meta: "PluginMeta") -> "PromptChatApiPluginMeta":
        """
        The contract's model of a plugin's metadata.

        :param plugin_meta: The row, whose tags should be prefetched.
        :type plugin_meta: smarter.apps.llmtool.models.PluginMeta
        :returns: The model.
        :rtype: PromptChatApiPluginMeta
        """
        return cls(
            id=plugin_meta.pk,
            created_at=plugin_meta.created_at,
            updated_at=plugin_meta.updated_at,
            name=plugin_meta.name,
            description=plugin_meta.description,
            version=plugin_meta.version,
            tags=[tag.name for tag in plugin_meta.tags.all()],
            annotations=plugin_meta.annotations,
            plugin_class=plugin_meta.plugin_class,  # type: ignore[arg-type]
        )


class PromptChatApiLLMClientPlugin(PromptChatApiOrmModel):
    """A plugin of the LLMClient: a :class:`smarter.apps.llmclient.models.LLMClientPlugin`."""

    llmclient: int = Field(..., description="LLMClientPlugin.llmclient: the LLMClient's id.")
    plugin_meta: PromptChatApiPluginMeta = Field(..., description="LLMClientPlugin.plugin_meta.")

    @classmethod
    def from_model(cls, plugin: "LLMClientPlugin") -> "PromptChatApiLLMClientPlugin":
        """
        The contract's model of a plugin of the LLMClient.

        :param plugin: The row, whose ``plugin_meta`` and its tags should be prefetched.
        :type plugin: smarter.apps.llmclient.models.LLMClientPlugin
        :returns: The model.
        :rtype: PromptChatApiLLMClientPlugin
        """
        return cls(
            id=plugin.pk,
            created_at=plugin.created_at,
            updated_at=plugin.updated_at,
            llmclient=plugin.llmclient_id,  # type: ignore[attr-defined]
            plugin_meta=PromptChatApiPluginMeta.from_model(plugin.plugin_meta),
        )


class PromptChatApiLLMClientFunction(PromptChatApiOrmModel):
    """A built-in function of the LLMClient: a :class:`smarter.apps.llmclient.models.LLMClientFunctions`."""

    llmclient: int = Field(..., description="LLMClientFunctions.llmclient: the LLMClient's id.")
    name: Optional[PromptChatApiFunctionName] = Field(None, description="LLMClientFunctions.name.")

    @classmethod
    def from_model(cls, function: "LLMClientFunctions") -> "PromptChatApiLLMClientFunction":
        """
        The contract's model of a built-in function of the LLMClient.

        :param function: The row.
        :type function: smarter.apps.llmclient.models.LLMClientFunctions
        :returns: The model.
        :rtype: PromptChatApiLLMClientFunction
        """
        return cls(
            id=function.pk,
            created_at=function.created_at,
            updated_at=function.updated_at,
            llmclient=function.llmclient_id,  # type: ignore[attr-defined]
            name=function.name,  # type: ignore[arg-type]
        )


class PromptChatApiPromptRequest(PromptChatApiModel):
    """The prompt api's request body: the chat thread, with only the roles that LLMs accept."""

    session_key: Optional[str] = None
    messages: list[PromptChatApiMessage]


class PromptChatApiLLMClientRequest(PromptChatApiOrmModel):
    """A request to the LLMClient's prompt api: a :class:`smarter.apps.llmclient.models.LLMClientRequests`."""

    llmclient: int = Field(..., description="LLMClientRequests.llmclient: the LLMClient's id.")
    request: Optional[PromptChatApiPromptRequest] = Field(None, description="LLMClientRequests.request.")
    session_key: Optional[str] = Field(None, description="LLMClientRequests.session_key.")
    is_aggregation: Optional[bool] = Field(None, description="LLMClientRequests.is_aggregation.")

    @classmethod
    def from_model(cls, row: "LLMClientRequests") -> "PromptChatApiLLMClientRequest":
        """
        The contract's model of a request to the LLMClient's prompt api.

        :param row: The row.
        :type row: smarter.apps.llmclient.models.LLMClientRequests
        :returns: The model.
        :rtype: PromptChatApiLLMClientRequest
        """
        return cls(
            id=row.pk,
            created_at=row.created_at,
            updated_at=row.updated_at,
            llmclient=row.llmclient_id,  # type: ignore[attr-defined]
            request=row.request,  # type: ignore[arg-type]
            session_key=row.session_key,
            is_aggregation=row.is_aggregation,
        )


@deprecated(V1_DEPRECATION)
class PromptChatApiLLMClientRequestV1(PromptChatApiOrmModel):
    """A request to the LLMClient's prompt api, in version 1, whose ``llmclient`` is renamed ``chatbot``."""

    chatbot: int = Field(..., description="LLMClientRequests.llmclient: the LLMClient's id.")
    request: Optional[PromptChatApiPromptRequest] = None
    session_key: Optional[str] = None
    is_aggregation: Optional[bool] = None


class PromptChatApiPromptToolCall(PromptChatApiOrmModel):
    """A tool call of the chat session: a :class:`smarter.apps.prompt.models.PromptToolCall`."""

    prompt: int = Field(..., description="PromptToolCall.prompt: the chat session's id.")
    plugin: Optional[int] = Field(None, description="PromptToolCall.plugin: the PluginMeta's id, for a plugin.")
    function_name: Optional[str] = Field(None, max_length=255, description="PromptToolCall.function_name.")
    function_args: Optional[str] = Field(None, max_length=255, description="PromptToolCall.function_args.")
    request: Optional[PromptChatApiJson] = Field(None, description="PromptToolCall.request: the tool's input.")
    response: Optional[PromptChatApiJson] = Field(None, description="PromptToolCall.response: the tool's result.")

    @classmethod
    def from_model(cls, row: "PromptToolCall") -> "PromptChatApiPromptToolCall":
        """
        The contract's model of a tool call of the chat session.

        :param row: The row.
        :type row: smarter.apps.prompt.models.PromptToolCall
        :returns: The model.
        :rtype: PromptChatApiPromptToolCall
        """
        return cls(
            id=row.pk,
            created_at=row.created_at,
            updated_at=row.updated_at,
            prompt=row.prompt_id,  # type: ignore[attr-defined]
            plugin=row.plugin_id,  # type: ignore[attr-defined]
            function_name=row.function_name,
            function_args=row.function_args,
            request=row.request,
            response=row.response,
        )


class PromptChatApiPromptPluginUsage(PromptChatApiOrmModel):
    """A plugin that the chat session used: a :class:`smarter.apps.prompt.models.PromptPluginUsage`."""

    prompt: int = Field(..., description="PromptPluginUsage.prompt: the chat session's id.")
    plugin: int = Field(..., description="PromptPluginUsage.plugin: the PluginMeta's id.")
    input_text: Optional[str] = Field(None, description="PromptPluginUsage.input_text.")

    @classmethod
    def from_model(cls, row: "PromptPluginUsage") -> "PromptChatApiPromptPluginUsage":
        """
        The contract's model of a plugin that the chat session used.

        :param row: The row.
        :type row: smarter.apps.prompt.models.PromptPluginUsage
        :returns: The model.
        :rtype: PromptChatApiPromptPluginUsage
        """
        return cls(
            id=row.pk,
            created_at=row.created_at,
            updated_at=row.updated_at,
            prompt=row.prompt_id,  # type: ignore[attr-defined]
            plugin=row.plugin_id,  # type: ignore[attr-defined]
            input_text=row.input_text,
        )


class PromptChatApiPluginSelection(PromptChatApiOrmModel):
    """A plugin selector's activation: a :class:`smarter.apps.llmtool.models.PluginSelectorHistory`."""

    plugin_selector: int = Field(..., description="PluginSelectorHistory.plugin_selector: the PluginSelector's id.")
    search_term: Optional[str] = Field(None, max_length=255, description="PluginSelectorHistory.search_term.")
    messages: Optional[list[PromptChatApiMessage]] = Field(None, description="PluginSelectorHistory.messages.")
    session_key: Optional[str] = Field(None, max_length=255, description="PluginSelectorHistory.session_key.")

    @classmethod
    def from_model(cls, row: "PluginSelectorHistory") -> "PromptChatApiPluginSelection":
        """
        The contract's model of a plugin selector's activation.

        :param row: The row.
        :type row: smarter.apps.llmtool.models.PluginSelectorHistory
        :returns: The model.
        :rtype: PromptChatApiPluginSelection
        """
        return cls(
            id=row.pk,
            created_at=row.created_at,
            updated_at=row.updated_at,
            plugin_selector=row.plugin_selector_id,  # type: ignore[attr-defined]
            search_term=row.search_term,
            messages=row.messages,  # type: ignore[arg-type]
            session_key=row.session_key,
        )


class PromptChatApiHistoryBase(BaseModel):
    """The chat session's history.

    It has exactly these fields.
    """

    model_config = ConfigDict(extra="forbid")

    chat_history: list[PromptChatApiMessage] = Field(
        default_factory=list, description="The session's messages, which restore the chat thread."
    )
    prompt_tool_call_history: Optional[list[PromptChatApiPromptToolCall]] = None
    prompt_plugin_usage_history: Optional[list[PromptChatApiPromptPluginUsage]] = None
    plugin_selector_history: Optional[list[PromptChatApiPluginSelection]] = None


class PromptChatApiHistory(PromptChatApiHistoryBase):
    """The chat session's history, in version 2.

    Only ``chat_history`` is public.
    """

    llmclient_request_history: Optional[list[PromptChatApiLLMClientRequest]] = None


@deprecated(V1_DEPRECATION)
class PromptChatApiHistoryV1(PromptChatApiHistoryBase):
    """The chat session's history, in version 1."""

    chatbot_request_history: Optional[list[PromptChatApiLLMClientRequestV1]] = None


class PromptChatApiMetaData(PromptChatApiModel):
    """The LLMClient's state."""

    ready: Optional[bool] = None
    is_valid: Optional[bool] = None
    is_deployed: Optional[bool] = None


class PromptChatApiListMetaData(PromptChatApiModel):
    """The counts of a list of the LLMClient's plugins or functions."""

    total_plugins: Optional[int] = None
    plugins_returned: Optional[int] = None
    total_functions: Optional[int] = None
    functions_returned: Optional[int] = None


class PromptChatApiPluginList(PromptChatApiModel):
    """The LLMClient's plugins.

    The list itself is returned only in the complete configuration.
    """

    meta_data: PromptChatApiListMetaData
    plugins: list[PromptChatApiLLMClientPlugin] = Field(default_factory=list)


class PromptChatApiFunctionList(PromptChatApiModel):
    """The LLMClient's built-in functions.

    The list itself is returned only in the complete configuration.
    """

    meta_data: PromptChatApiListMetaData
    functions: list[PromptChatApiLLMClientFunction] = Field(default_factory=list)


@deprecated(V1_DEPRECATION)
class PromptChatApiLLMClientPluginV1(PromptChatApiOrmModel):
    """A plugin of the LLMClient, in version 1, whose ``llmclient`` is renamed ``chatbot``."""

    chatbot: int = Field(..., description="LLMClientPlugin.llmclient: the LLMClient's id.")
    plugin_meta: PromptChatApiPluginMeta


@deprecated(V1_DEPRECATION)
class PromptChatApiLLMClientFunctionV1(PromptChatApiOrmModel):
    """A built-in function of the LLMClient, in version 1, whose ``llmclient`` is renamed ``chatbot``."""

    chatbot: int = Field(..., description="LLMClientFunctions.llmclient: the LLMClient's id.")
    name: Optional[PromptChatApiFunctionName] = None


@deprecated(V1_DEPRECATION)
class PromptChatApiPluginListV1(PromptChatApiModel):
    """The LLMClient's plugins, in version 1."""

    meta_data: PromptChatApiListMetaData
    plugins: list[PromptChatApiLLMClientPluginV1] = Field(default_factory=list)


@deprecated(V1_DEPRECATION)
class PromptChatApiFunctionListV1(PromptChatApiModel):
    """The LLMClient's built-in functions, in version 1."""

    meta_data: PromptChatApiListMetaData
    functions: list[PromptChatApiLLMClientFunctionV1] = Field(default_factory=list)


class PromptChatApiConfigBase(PromptChatApiModel):
    """The configuration's fields that both versions share."""

    session_key: str = Field(..., pattern=SESSION_KEY_PATTERN, description="The chat session's key.")
    sandbox_mode: bool = Field(..., description="True for a workbench url.")
    debug_mode: bool = Field(..., description="The ENABLE_REACTAPP_DEBUG_MODE waffle switch.")
    meta_data: PromptChatApiMetaData


class PromptChatApiConfig(PromptChatApiConfigBase):
    """
    The configuration, version 2.

    ``PromptConfigView.config()`` builds one, from which every response is derived:
    :meth:`public` for a deployed LLMClient's own host, and :meth:`to_v1` for older clients.
    """

    contract: Literal[2] = CHAT_CONTRACT_V2
    llmclient: PromptChatApiLLMClient
    history: PromptChatApiHistory
    plugins: PromptChatApiPluginList
    functions: Optional[PromptChatApiFunctionList] = None

    def public(self) -> "PromptChatApiConfig":
        """
        The public configuration.

        A deployed LLMClient's own host returns it to the pages that embed Smarter Chat.

        The LLMClient is reduced to :data:`~.const.PUBLIC_LLMCLIENT_FIELDS`, without e.g. its owner's
        profile, the history to the session's own messages, without the requests that Smarter sent to
        the LLM, the meta data to :data:`~.const.PUBLIC_META_DATA_FIELDS`, and the plugins and functions
        to their counts.

        :returns: A new configuration.
        :rtype: PromptChatApiConfig
        """
        llmclient = self.llmclient.model_dump(exclude_unset=True)
        meta_data = self.meta_data.model_dump(exclude_unset=True)
        return PromptChatApiConfig(
            contract=CHAT_CONTRACT_V2,
            session_key=self.session_key,
            sandbox_mode=self.sandbox_mode,
            debug_mode=self.debug_mode,
            llmclient=PromptChatApiLLMClient(
                **{key: llmclient[key] for key in PUBLIC_LLMCLIENT_FIELDS if key in llmclient}
            ),
            history=PromptChatApiHistory(chat_history=self.history.chat_history),
            meta_data=PromptChatApiMetaData(
                **{key: meta_data[key] for key in PUBLIC_META_DATA_FIELDS if key in meta_data}
            ),
            plugins=PromptChatApiPluginList(meta_data=self.plugins.meta_data, plugins=[]),
            functions=(
                PromptChatApiFunctionList(meta_data=self.functions.meta_data, functions=[]) if self.functions else None
            ),
        )

    @deprecated(V1_DEPRECATION)
    def to_v1(self) -> "PromptChatApiConfigV1":
        """
        The same configuration, in version 1 of the contract.

        Its keys are renamed at every depth: see :data:`LEGACY_KEY_RENAMES`.

        :returns: The version 1 configuration.
        :rtype: PromptChatApiConfigV1
        """
        data = self.model_dump(mode="json", exclude_unset=True, exclude={"contract"})
        return PromptChatApiConfigV1.model_validate(legacy_key_names(data))


@deprecated(V1_DEPRECATION)
class PromptChatApiConfigV1(PromptChatApiConfigBase):
    """The configuration, version 1."""

    chatbot: PromptChatApiChatbotV1
    history: PromptChatApiHistoryV1
    plugins: PromptChatApiPluginListV1
    functions: Optional[PromptChatApiFunctionListV1] = None


class PromptChatApiConfigRequest(PromptChatApiModel):
    """The configuration api's request body."""

    session_key: Optional[str] = Field(None, description="The chat session's key, or empty for a new session.")


class PromptChatApiConfigResponse(PromptChatApiEnvelope):
    """The configuration api's response, version 2."""

    data: PromptChatApiConfig


@deprecated(V1_DEPRECATION)
class PromptChatApiConfigResponseV1(PromptChatApiEnvelope):
    """The configuration api's response, version 1."""

    data: PromptChatApiConfigV1


# ------------------------------------------------------------------------------
# the prompt api
# ------------------------------------------------------------------------------


class PromptChatApiChoice(PromptChatApiModel):
    """A choice of a chat completion."""

    index: int = 0
    finish_reason: Optional[str] = Field(None, description="e.g. stop, length or tool_calls.")
    message: Optional[PromptChatApiMessage] = None


class PromptChatApiTokenDetails(PromptChatApiModel):
    """The breakdown of a completion's tokens."""

    reasoning_tokens: Optional[int] = None
    cached_tokens: Optional[int] = None
    audio_tokens: Optional[int] = None


class PromptChatApiUsage(PromptChatApiModel):
    """A chat completion's token usage."""

    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None
    prompt_tokens_details: Optional[PromptChatApiTokenDetails] = None
    completion_tokens_details: Optional[PromptChatApiTokenDetails] = None


class PromptChatApiCompletion(BaseModel):
    """
    The LLM's chat completion, in the format of the OpenAI api, with only these fields.

    Smarter's own additions, ``smarter`` and ``metadata``, are not part of it: the messages, plugins and
    tools are in :class:`PromptChatApiPromptResult`, and ``metadata``, which describes the tool calls
    with their plugins' owners, is returned only to the cli.
    """

    model_config = ConfigDict(extra="ignore")

    id: Optional[str] = None
    object: Optional[str] = None
    created: Optional[int] = None
    model: Optional[str] = None
    choices: list[PromptChatApiChoice] = Field(default_factory=list)
    usage: Optional[PromptChatApiUsage] = None
    system_fingerprint: Optional[str] = None
    service_tier: Optional[str] = None


class PromptChatApiPromptResult(PromptChatApiModel):
    """The result of a prompt, version 2."""

    contract: Literal[2] = CHAT_CONTRACT_V2
    status: int = Field(..., description="The prompt's http status: 200, or the LLM provider's error status.")
    messages: list[PromptChatApiMessage] = Field(
        default_factory=list, description="The messages that the prompt added to the chat thread, in order."
    )
    completion: Optional[PromptChatApiCompletion] = Field(
        None,
        description="The LLM's chat completion, in the format of the OpenAI api: its choices and usage.",
    )
    plugins: list[str] = Field(default_factory=list, description="The plugins that Smarter selected.")
    tools: list[str] = Field(default_factory=list, description="The functions that the LLM could call.")


class PromptChatApiPromptResponse(PromptChatApiEnvelope):
    """
    The prompt api's response, version 2.

    A failed prompt has ``error`` too, and its http status is the LLM provider's. Its ``data.messages``
    include a ``smarter_error`` message, which is also saved in the session's history.
    """

    data: PromptChatApiPromptResult
    error: Optional[PromptChatApiErrorBody] = None


@deprecated(V1_DEPRECATION)
class PromptChatApiLambdaResponseV1(PromptChatApiModel):
    """A prompt's result, version 1: an AWS Lambda style response, whose body is a JSON string."""

    isBase64Encoded: bool = False
    statusCode: int
    headers: dict[str, str] = Field(default_factory=dict)
    body: str = Field(..., description="A PromptChatApiCompletionV1, or a PromptChatApiFailureV1, as a JSON string.")


@deprecated(V1_DEPRECATION)
class PromptChatApiSmarterCompletionV1(PromptChatApiModel):
    """Smarter's additions to a completion, version 1."""

    messages: list[PromptChatApiMessage] = Field(default_factory=list)
    plugins: list[str] = Field(default_factory=list)
    tools: list[str] = Field(default_factory=list)


@deprecated(V1_DEPRECATION)
class PromptChatApiCompletionV1(PromptChatApiModel):
    """The parsed body of a successful prompt, version 1: a chat completion, with Smarter's additions."""

    smarter: PromptChatApiSmarterCompletionV1


@deprecated(V1_DEPRECATION)
class PromptChatApiProviderErrorV1(PromptChatApiModel):
    """The LLM provider's error, version 1."""

    status: int
    message: str


@deprecated(V1_DEPRECATION)
class PromptChatApiFailureV1(PromptChatApiModel):
    """The parsed body of a failed prompt, version 1."""

    error: PromptChatApiProviderErrorV1
    response: PromptChatApiCompletionV1


@deprecated(V1_DEPRECATION)
class PromptChatApiPromptResponseV1(PromptChatApiEnvelope):
    """The prompt api's response, version 1."""

    data: PromptChatApiLambdaResponseV1


# ------------------------------------------------------------------------------
# the prompt's Server-Sent Events
# ------------------------------------------------------------------------------


class PromptChatApiProgressEvent(PromptChatApiModel):
    """The data of a ``progress`` event: a step of a running prompt."""

    type: PromptChatApiProgressEventType
    message: str = Field(..., description="A short sentence, which Smarter Chat displays as is.")


class PromptChatApiProgressResult(PromptChatApiModel):
    """The data of the final ``result`` event."""

    status: int = Field(..., description="The prompt's http status.")
    response: Union[PromptChatApiPromptResponse, PromptChatApiPromptResponseV1, PromptChatApiErrorResponse] = Field(
        ..., description="Exactly the JSON of a non-streaming response."
    )


CONTRACT_MODELS: tuple[type[BaseModel], ...] = (
    PromptChatApiMessage,
    PromptChatApiErrorBody,
    PromptChatApiErrorResponse,
    PromptChatApiConfigRequest,
    PromptChatApiConfigResponse,
    PromptChatApiConfigResponseV1,
    PromptChatApiPromptRequest,
    PromptChatApiPromptResponse,
    PromptChatApiPromptResponseV1,
    PromptChatApiCompletionV1,
    PromptChatApiFailureV1,
    PromptChatApiProgressEvent,
    PromptChatApiProgressResult,
)
"""The models whose JSON Schema is exported.

Their dependencies are exported with them.
"""

__all__ = [
    "CONTRACT_MODELS",
    "LEGACY_KEY_RENAMES",
    "legacy_key_names",
    "PromptChatApiEnvelope",
    "PromptChatApiChatbotV1",
    "PromptChatApiConfig",
    "PromptChatApiConfigRequest",
    "PromptChatApiConfigResponse",
    "PromptChatApiConfigResponseV1",
    "PromptChatApiConfigV1",
    "PromptChatApiErrorBody",
    "PromptChatApiErrorResponse",
    "PromptChatApiHistory",
    "PromptChatApiHistoryV1",
    "PromptChatApiMessage",
    "PromptChatApiMetaData",
    "PromptChatApiFunctionList",
    "PromptChatApiLambdaResponseV1",
    "PromptChatApiLLMClient",
    "PromptChatApiFunctionName",
    "PromptChatApiLLMClientFunction",
    "PromptChatApiLLMClientPlugin",
    "PromptChatApiOrmModel",
    "PromptChatApiPluginClass",
    "PromptChatApiPluginList",
    "PromptChatApiPluginMeta",
    "PromptChatApiLLMClientPluginV1",
    "PromptChatApiLLMClientFunctionV1",
    "PromptChatApiPluginListV1",
    "PromptChatApiFunctionListV1",
    "PromptChatApiProgressEvent",
    "PromptChatApiProgressEventType",
    "PromptChatApiProgressResult",
    "PromptChatApiCompletionV1",
    "PromptChatApiFailureV1",
    "PromptChatApiProviderErrorV1",
    "PromptChatApiPromptRequest",
    "PromptChatApiPromptResponse",
    "PromptChatApiPromptResponseV1",
    "PromptChatApiPromptResult",
    "PromptChatApiListMetaData",
    "PromptChatApiSmarterCompletionV1",
    "PromptChatApiStyles",
    "PromptChatApiStyleSection",
    "PromptChatApiAudioPart",
    "PromptChatApiChoice",
    "PromptChatApiCompletion",
    "PromptChatApiContentPart",
    "PromptChatApiFilePart",
    "PromptChatApiFileRef",
    "PromptChatApiFunctionCall",
    "PromptChatApiImagePart",
    "PromptChatApiImageUrl",
    "PromptChatApiInputAudio",
    "PromptChatApiJournalMetadata",
    "PromptChatApiJson",
    "PromptChatApiLLMClientRequest",
    "PromptChatApiLLMClientRequestV1",
    "PromptChatApiPluginSelection",
    "PromptChatApiPromptPluginUsage",
    "PromptChatApiPromptToolCall",
    "PromptChatApiRefusalPart",
    "PromptChatApiTextPart",
    "PromptChatApiTokenDetails",
    "PromptChatApiToolCall",
    "PromptChatApiUsage",
]
