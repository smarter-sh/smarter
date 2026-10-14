"""
Pydantic models of the prompt history's REST api responses (``/api/v1/prompts/history/``).

The prompt history is the chat sessions (:class:`PromptHistoryApiSession`) of the users whose
resources the requesting user may manage, the tool calls that the LLMs made in them
(:class:`PromptHistoryApiToolCall`), and the plugins that they used
(:class:`PromptHistoryApiPluginUsage`).

The models are the outputs of the serializers of :mod:`smarter.apps.prompt.api.v1.serializers`,
which the REST api returned before it was modeled, and which clients already read. Their keys are
snake_case, unlike the rest of the REST api's, for the same reason. A plugin is a
:class:`smarter.apps.llmtool.contract.models.PluginApiPluginMeta`, in camelCase.

The models forbid extra fields: the api returns exactly what they declare.
"""

from datetime import datetime
from typing import TYPE_CHECKING, Optional

from pydantic import BaseModel, ConfigDict, Field, JsonValue

from smarter.apps.account.contract.models import MetaDataApiAnnotations
from smarter.apps.llmtool.contract.models import PluginApiPluginMeta

if TYPE_CHECKING:
    from smarter.apps.prompt.models import Prompt, PromptPluginUsage, PromptToolCall


class PromptHistoryApiModel(BaseModel):
    """Base class of the prompt history's models: the fields of a row, and a TimestampedModel's."""

    model_config = ConfigDict(extra="forbid")

    id: int = Field(..., description="The row's primary key.")
    created_at: Optional[datetime] = Field(None, description="TimestampedModel.created_at.")
    updated_at: Optional[datetime] = Field(None, description="TimestampedModel.updated_at.")


class PromptHistoryApiSession(PromptHistoryApiModel):
    """A chat session: one conversation with an LLMClient, a :class:`smarter.apps.prompt.models.Prompt`."""

    name: str = Field("", description="MetaDataModel.name.")
    description: Optional[str] = Field(None, description="MetaDataModel.description.")
    version: Optional[str] = Field(None, description="MetaDataModel.version, e.g. 1.0.0.")
    annotations: MetaDataApiAnnotations = Field(None, description="MetaDataModel.annotations.")
    session_key: str = Field(..., max_length=255, description="Prompt.session_key, which identifies the session.")
    ip_address: str = Field(..., description="Prompt.ip_address: the client's IP address.")
    user_agent: str = Field(..., max_length=255, description="Prompt.user_agent: the client's user agent.")
    url: str = Field(..., description="Prompt.url: the url that the session's chat was configured with.")
    user_profile: int = Field(..., description="Prompt.user_profile: the user profile's id.")
    llmclient: int = Field(..., description="Prompt.llmclient: the LLMClient's id.")

    @classmethod
    def from_model(cls, prompt: "Prompt") -> "PromptHistoryApiSession":
        """
        The contract's model of a chat session.

        :param prompt: The row.
        :type prompt: smarter.apps.prompt.models.Prompt
        :returns: The model.
        :rtype: PromptHistoryApiSession
        """
        return cls(
            id=prompt.pk,
            created_at=prompt.created_at,
            updated_at=prompt.updated_at,
            name=prompt.name,
            description=prompt.description,
            version=prompt.version,
            annotations=prompt.annotations,
            session_key=prompt.session_key,
            ip_address=prompt.ip_address,
            user_agent=prompt.user_agent,
            url=prompt.url,
            user_profile=prompt.user_profile_id,  # type: ignore[attr-defined]
            llmclient=prompt.llmclient_id,  # type: ignore[attr-defined]
        )


class PromptHistoryApiToolCall(PromptHistoryApiModel):
    """A tool call that the LLM made in a chat session: a :class:`smarter.apps.prompt.models.PromptToolCall`."""

    prompt: PromptHistoryApiSession = Field(..., description="PromptToolCall.prompt: the chat session.")
    plugin: Optional[int] = Field(None, description="PromptToolCall.plugin: the PluginMeta's id, for a plugin.")
    function_name: Optional[str] = Field(None, max_length=255, description="PromptToolCall.function_name.")
    function_args: Optional[str] = Field(None, max_length=255, description="PromptToolCall.function_args.")
    request: Optional[JsonValue] = Field(None, description="PromptToolCall.request: the tool's input.")
    response: Optional[JsonValue] = Field(None, description="PromptToolCall.response: the tool's result.")

    @classmethod
    def from_model(cls, row: "PromptToolCall") -> "PromptHistoryApiToolCall":
        """
        The contract's model of a tool call.

        :param row: The row, whose ``prompt`` should be fetched with it.
        :type row: smarter.apps.prompt.models.PromptToolCall
        :returns: The model.
        :rtype: PromptHistoryApiToolCall
        """
        return cls(
            id=row.pk,
            created_at=row.created_at,
            updated_at=row.updated_at,
            prompt=PromptHistoryApiSession.from_model(row.prompt),
            plugin=row.plugin_id,  # type: ignore[attr-defined]
            function_name=row.function_name,
            function_args=row.function_args,
            request=row.request,
            response=row.response,
        )


class PromptHistoryApiPluginUsage(PromptHistoryApiModel):
    """A use of a plugin in a chat session: a :class:`smarter.apps.prompt.models.PromptPluginUsage`."""

    prompt: PromptHistoryApiSession = Field(..., description="PromptPluginUsage.prompt: the chat session.")
    plugin: PluginApiPluginMeta = Field(..., description="PromptPluginUsage.plugin: the plugin.")
    input_text: Optional[str] = Field(None, description="PromptPluginUsage.input_text.")

    @classmethod
    def from_model(cls, row: "PromptPluginUsage", user: object = None) -> "PromptHistoryApiPluginUsage":
        """
        The contract's model of a use of a plugin.

        :param row: The row, whose ``prompt`` and ``plugin`` should be fetched with it.
        :type row: smarter.apps.prompt.models.PromptPluginUsage
        :param user: The requesting user, for the plugin's ``canDelete``. None may delete nothing.
        :type user: object
        :returns: The model.
        :rtype: PromptHistoryApiPluginUsage
        """
        return cls(
            id=row.pk,
            created_at=row.created_at,
            updated_at=row.updated_at,
            prompt=PromptHistoryApiSession.from_model(row.prompt),
            plugin=PluginApiPluginMeta.from_model(row.plugin, user),
            input_text=row.input_text,
        )


PROMPT_HISTORY_API_MODELS = (PromptHistoryApiSession, PromptHistoryApiToolCall, PromptHistoryApiPluginUsage)
"""The models whose JSON Schemas the Smarter api's OpenAPI document includes."""

__all__ = [
    "PROMPT_HISTORY_API_MODELS",
    "PromptHistoryApiModel",
    "PromptHistoryApiPluginUsage",
    "PromptHistoryApiSession",
    "PromptHistoryApiToolCall",
]
