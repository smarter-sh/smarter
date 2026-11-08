"""
Enumerations of the keys and values of OpenAI's function calling tool definitions, and of its reasoning efforts.

A tool definition looks like this, e.g. as a plugin builds it:

.. code-block:: python

    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "Get the current weather in a city.",
            "parameters": {
                "type": "object",
                "properties": properties,
                "required": [],
            },
        },
    }
"""

from typing import Literal, get_args

from smarter.common.enum import SmarterEnumAbstract

OpenAIReasoningEffort = Literal["none", "minimal", "low", "medium", "high", "xhigh"]
"""
The values of the chat completions api's ``reasoning_effort``, from the least reasoning to the most.

Each reasoning model supports some of them: e.g. gpt-6-luna supports 'none' to 'xhigh' but not
'minimal', and gpt-6.1-sol doesn't support 'none'. Models that don't reason, such as gpt-4o, reject
the parameter altogether. See :mod:`smarter.lib.openai.model_quirks`.
"""

OPENAI_REASONING_EFFORTS: tuple[str, ...] = get_args(OpenAIReasoningEffort)
"""The values of :data:`OpenAIReasoningEffort`, in order."""


class OpenAIToolCall(SmarterEnumAbstract):
    """Enum for OpenAI function calling types."""

    TYPE = "type"
    FUNCTION = "function"
    NAME = "name"
    DESCRIPTION = "description"
    DEFAULT = "default"
    PARAMETERS = "parameters"
    OBJECT = "object"
    PROPERTIES = "properties"
    REQUIRED = "required"

    @classmethod
    def all(cls) -> list["OpenAIToolCall"]:
        """
        Return the members that a tool definition uses: every member except ``DEFAULT``.

        :returns: The members, not their values.
        """
        members = [
            cls.TYPE,
            cls.FUNCTION,
            cls.NAME,
            cls.DESCRIPTION,
            cls.PARAMETERS,
            cls.OBJECT,
            cls.PROPERTIES,
            cls.REQUIRED,
        ]
        return members


class OpenAIToolTypes(SmarterEnumAbstract):
    """Enum for OpenAI tool types."""

    FUNCTION = "function"
    CODE_INTERPRETER = "code_interpreter"
    RETRIEVAL = "retrieval"

    @classmethod
    def all(cls) -> list["OpenAIToolTypes"]:
        """
        Return every member.

        :returns: The members, not their values.
        """
        members = [
            cls.FUNCTION,
            cls.CODE_INTERPRETER,
            cls.RETRIEVAL,
        ]
        return members
