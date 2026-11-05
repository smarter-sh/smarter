"""
Enumerations of the keys and values of OpenAI's function calling tool definitions.

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

from smarter.common.enum import SmarterEnumAbstract


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
