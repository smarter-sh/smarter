# -*- coding: utf-8 -*-
"""Example of
a.) how to customize the system prompt to adapt to keywords in the user's message
b.) how to call a function from the model
"""
import json

from django.contrib.auth.models import User

from smarter.apps.chat.signals import plugin_called

# from .plugin_loader import Plugin, plugins
from smarter.apps.plugin.plugin import Plugin
from smarter.apps.plugin.utils import plugins_for_user

from .natural_language_processing import does_refer_to


def search_terms_are_in_messages(messages: list, search_terms: list) -> bool:
    """
    Return True the user has mentioned Lawrence McDaniel or FullStackWithLawrence
    at any point in the history of the conversation.

    messages: [{"role": "user", "content": "some text"}]
    search_terms: ["Lawrence McDaniel", "FullStackWithLawrence"]
    search_pairs: [["Lawrence", "McDaniel"], ["FullStackWithLawrence", "Lawrence McDaniel"]]
    """
    for message in messages:
        if "role" in message and str(message["role"]).lower() == "user":
            content = message["content"]
            for term in search_terms:
                if does_refer_to(prompt=content, refers_to=term):
                    return True

    return False


def customized_prompt(plugin: Plugin, messages: list) -> list:
    """Modify the system prompt based on the plugin object"""

    for i, message in enumerate(messages):
        if message.get("role") == "system":
            system_role = message.get("content")
            custom_prompt = {
                "role": "system",
                "content": system_role + "\n\n and also " + plugin.plugin_prompt.system_role,
            }
            messages[i] = custom_prompt
            break

    return messages


# pylint: disable=too-many-return-statements
def function_calling_plugin(user: User, inquiry_type: str) -> str:
    """Return select info from custom plugin object"""

    plugin_called.send(sender=function_calling_plugin, user=user, inquiry_type=inquiry_type)
    for plugin in plugins_for_user(user=user):
        try:
            return_data = plugin.plugin_data.return_data
            retval = return_data[inquiry_type]
            return json.dumps(retval)
        except KeyError:
            pass

    raise KeyError(f"Invalid inquiry_type: {inquiry_type}")


def plugin_tool_factory(plugin: Plugin):
    """
    Return a dictionary of chat completion tools.
    """
    tool = {
        "type": "function",
        "function": {
            "name": "function_calling_plugin",
            "description": plugin.plugin_data.description,
            "parameters": {
                "type": "object",
                "properties": {
                    "inquiry_type": {
                        "type": "string",
                        "enum": plugin.plugin_data.return_data_keys,
                    },
                },
                "required": ["inquiry_type"],
            },
        },
    }
    return tool
