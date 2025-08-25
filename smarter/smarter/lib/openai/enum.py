"""
This module defines an enumeration for OpenAI function calling types.

"type": "function",
"function": {
    "name": self.function_calling_identifier,
    "description": self.plugin_meta.description if self.plugin_meta else "No description provided.",
    "parameters": {
        "type": "object",
        "properties": properties,
        "required": [],
    },

"""

from smarter.common.enum import SmarterEnumAbstract


class OpenAIToolCall(SmarterEnumAbstract):
    """
    Enum for OpenAI function calling types.
    """

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
    def all(cls):
        return [
            cls.TYPE,
            cls.FUNCTION,
            cls.NAME,
            cls.DESCRIPTION,
            cls.PARAMETERS,
            cls.OBJECT,
            cls.PROPERTIES,
            cls.REQUIRED,
        ]


class OpenAIToolTypes(SmarterEnumAbstract):
    """
    Enum for OpenAI tool types.
    """

    FUNCTION = "function"
    CODE_INTERPRETER = "code_interpreter"
    RETRIEVAL = "retrieval"

    @classmethod
    def all(cls):
        return [
            cls.FUNCTION,
            cls.CODE_INTERPRETER,
            cls.RETRIEVAL,
        ]
