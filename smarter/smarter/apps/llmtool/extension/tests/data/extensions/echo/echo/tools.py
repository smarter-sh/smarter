"""The echo extension's tools."""

import time

from pydantic import BaseModel

from smarter.apps.llmtool.extension import (
    ExtensionContext,
    ExtensionToolError,
    SmarterExtensionTool,
)

from .models import EchoArguments, NoArguments


class Echo(SmarterExtensionTool):
    """Echo the text that it is sent, after a greeting."""

    name = "echo"
    arguments_model = EchoArguments

    def call(self, arguments: BaseModel, context: ExtensionContext):
        if not isinstance(arguments, EchoArguments):
            raise ExtensionToolError("the arguments are not EchoArguments.")
        # the settings model is created at run time from the manifest, so its attributes are read with getattr().
        settings = context.settings
        greeting = getattr(settings, "greeting")
        repeat = getattr(settings, "repeat")
        api_key = getattr(settings, "api_key")
        result = {
            "echo": " ".join([f"{greeting} {arguments.text}"] * repeat),
            "has_api_key": api_key is not None,
            "account": context.account.account_number if context.account else None,
        }
        if context.switch_is_active("verbose"):
            result["version"] = context.version
        return result


class Fail(SmarterExtensionTool):
    """Always raise an unexpected exception."""

    name = "fail"
    arguments_model = NoArguments

    def call(self, arguments, context):
        raise RuntimeError("this tool always fails")


class Refuse(SmarterExtensionTool):
    """Always refuse, with a message for the LLM."""

    name = "refuse"
    arguments_model = NoArguments

    def call(self, arguments, context):
        raise ExtensionToolError("I refuse")


class Slow(SmarterExtensionTool):
    """Take longer than the extension's timeout."""

    name = "slow"
    arguments_model = NoArguments

    def call(self, arguments, context):
        time.sleep(5)
        return "too late"


class Unserializable(SmarterExtensionTool):
    """Return something that is not JSON."""

    name = "unserializable"
    arguments_model = NoArguments

    def call(self, arguments, context):
        return {"value": object()}
