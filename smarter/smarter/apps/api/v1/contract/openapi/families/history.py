"""The prompt history's REST reads, under ``/api/v1/prompts/history/``: the chat sessions, their tool calls and plugin usage."""

from smarter.apps.api.v1.contract.models import OpenApiPathItem
from smarter.apps.api.v1.contract.openapi.builders import (
    ApiFamily,
    integer_id,
    plural,
    rest_read,
)
from smarter.apps.api.v1.contract.openapi.families.llmclient import LLMCLIENTS
from smarter.apps.prompt.const import namespace as prompt_namespace
from smarter.apps.prompt.contract.history import (
    PromptHistoryApiPluginUsage,
    PromptHistoryApiSession,
    PromptHistoryApiToolCall,
)

HISTORY = ApiFamily(
    name="history",
    resource="chat session",
    urlconf="smarter.apps.prompt.api.v1.urls",
    description="The {plural}, and their tool calls and plugin usage.",
    mount=plural(prompt_namespace),
    tag_name="history",
)
"""
The prompt history's family: a feature of the prompt app, whose routes are under the app's ``/prompts/``.

Its operations' ids and its tag are the feature's name, history, not the app's.
"""

HISTORY_PERMISSION = (
    "Requires an api key. The response includes only the chat sessions whose user the user may manage: their "
    "own, their account's users' for an account admin, and every one for a superuser."
)
"""The note of the prompt history's reads."""


def history_paths() -> dict[str, OpenApiPathItem]:
    """
    The prompt history's REST reads, relative to the server's ``/api/v1``, newest first.

    :returns: The paths, e.g. ``{"/prompts/history/prompt/": ...}``.
    :rtype: dict[str, OpenApiPathItem]
    """
    family = HISTORY
    row_id = integer_id("id", "The row's id.")

    def read(action, summary, description, item, parameters, many=False):
        return rest_read(
            family.operation_id(action),
            summary,
            description,
            family.tag,
            item,
            many=many,
            parameters=parameters,
            note=HISTORY_PERMISSION,
        )

    return {
        family.path("history/prompt/"): OpenApiPathItem(
            get=read(
                "session_list",
                f"List {family.plural}",
                f"The {family.plural}: each conversation with {LLMCLIENTS.a}.",
                PromptHistoryApiSession.__name__,
                [],
                True,
            )
        ),
        family.path("history/prompt/{id}/"): OpenApiPathItem(
            get=read(
                "session_retrieve",
                family.a_capitalized,
                f"{family.a_capitalized}.",
                PromptHistoryApiSession.__name__,
                [row_id],
            )
        ),
        family.path("history/tool-calls/"): OpenApiPathItem(
            get=read(
                "tool_call_list",
                "List tool calls",
                f"The tool calls that the LLMs made in the {family.plural}, with their input and result.",
                PromptHistoryApiToolCall.__name__,
                [],
                True,
            )
        ),
        family.path("history/tool-calls/{id}/"): OpenApiPathItem(
            get=read("tool_call_retrieve", "A tool call", "A tool call.", PromptHistoryApiToolCall.__name__, [row_id])
        ),
        family.path("history/plugin-usage/"): OpenApiPathItem(
            get=read(
                "plugin_usage_list",
                "List plugin usage",
                f"The plugins that the {family.plural} used.",
                PromptHistoryApiPluginUsage.__name__,
                [],
                True,
            )
        ),
        family.path("history/plugin-usage/{id}/"): OpenApiPathItem(
            get=read(
                "plugin_usage_retrieve",
                "A plugin usage",
                f"A use of a plugin in {family.a}.",
                PromptHistoryApiPluginUsage.__name__,
                [row_id],
            )
        ),
    }


__all__ = ["HISTORY", "HISTORY_PERMISSION", "history_paths"]
