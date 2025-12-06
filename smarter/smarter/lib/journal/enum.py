"""Smarter API Manifests Enumerations."""

import logging
from typing import Optional
from urllib.parse import urlparse

from smarter.common.enum import SmarterEnumAbstract
from smarter.common.exceptions import SmarterException


logger = logging.getLogger(__name__)


class SmarterJournalEnumException(SmarterException):
    """Base exception for Smarter API Manifest enumerations."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Manifest Enumeration Error"


###############################################################################
# Smarter API cli response Enumerations
###############################################################################
class SmarterJournalApiResponseKeys:
    """Smarter API cli response keys."""

    API = "api"
    THING = "thing"
    METADATA = "metadata"
    DATA = "data"
    ERROR = "error"
    MESSAGE = "message"


class SmarterJournalApiResponseErrorKeys:
    """Smarter API cli response error keys."""

    ERROR_CLASS = "errorClass"
    STACK_TRACE = "stacktrace"
    DESCRIPTION = "description"
    STATUS = "status"
    ARGS = "args"
    CAUSE = "cause"
    CONTEXT = "context"


class SCLIResponseMetadata:
    """CLI get response metadata enumeration."""

    KEY = "key"
    COMMAND = "command"


class SmarterJournalThings(SmarterEnumAbstract):
    """
    Enumerates the types of objects ("things") that can be added to the Smarter Journal.

    This class descends from :class:`SmarterEnumAbstract`, typically implemented as a subclassed Singleton.
    For flexibility, it also allows instantiation with a string value, enabling a ``SmarterJournalThings`` value
    to be passed as a strongly typed object.

    Each member represents a resource type within the Smarter API, such as plugins, connections, accounts,
    authentication tokens, users, chats, providers, and secrets.

    Example usage::

        thing = SmarterJournalThings("Plugin")
        assert thing == SmarterJournalThings.STATIC_PLUGIN

    """

    STATIC_PLUGIN = "Plugin"
    """Smarter Static Plugin AI resource. A collection of Django ORM model instances."""

    API_PLUGIN = "ApiPlugin"
    """Smarter API Plugin AI resource. A Django ORM model instance."""

    SQL_PLUGIN = "SqlPlugin"
    """Smarter SQL Plugin AI resource. A Django ORM model instance."""

    API_CONNECTION = "ApiConnection"
    """Smarter API Connection resource. A Django ORM model instance."""

    SQL_CONNECTION = "SqlConnection"
    """Smarter SQL Connection resource. A Django ORM model instance."""

    ACCOUNT = "Account"
    """Smarter Account resource. A Django ORM model instance."""

    AUTH_TOKEN = "AuthToken"
    """Smarter Authentication Token resource. A Django DRF Knox subclass ORM model instance."""

    USER = "User"
    """Smarter User resource. A Django Auth User model instance."""

    CHAT = "Chat"
    """Smarter Chat resource. A Django ORM model instance."""

    CHAT_CONFIG = "ChatConfig"
    """Smarter ChatConfig resource. A JSON dictionary generated real-time"""

    CHAT_HISTORY = "ChatHistory"
    """Smarter ChatHistory resource. A list of Django ORM model instances."""

    CHAT_PLUGIN_USAGE = "ChatPluginUsage"
    """Smarter ChatPluginUsage resource. A list of Django ORM model instances."""

    CHAT_TOOL_CALL = "ChatToolCall"
    """Smarter ChatToolCall resource. A list of Django ORM model instances."""

    CHATBOT = "Chatbot"
    """Smarter Chatbot resource. A Django ORM model instance."""

    PROVIDER = "Provider"
    """Smarter Provider resource. A Django ORM model instance."""

    SECRET = "Secret"
    """Smarter Secret resource. A Django ORM model instance."""

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Django model choices for SmarterJournalThings."""
        return [
            (cls.STATIC_PLUGIN.value, cls.STATIC_PLUGIN.value),
            (cls.API_PLUGIN.value, cls.API_PLUGIN.value),
            (cls.SQL_PLUGIN.value, cls.SQL_PLUGIN.value),
            (cls.API_CONNECTION.value, cls.API_CONNECTION.value),
            (cls.SQL_CONNECTION.value, cls.SQL_CONNECTION.value),
            (cls.ACCOUNT.value, cls.ACCOUNT.value),
            (cls.AUTH_TOKEN.value, cls.AUTH_TOKEN.value),
            (cls.USER.value, cls.USER.value),
            (cls.CHAT.value, cls.CHAT.value),
            (cls.CHAT_CONFIG.value, cls.CHAT_CONFIG.value),
            (cls.CHAT_HISTORY.value, cls.CHAT_HISTORY.value),
            (cls.CHAT_PLUGIN_USAGE.value, cls.CHAT_PLUGIN_USAGE.value),
            (cls.CHAT_TOOL_CALL.value, cls.CHAT_TOOL_CALL.value),
            (cls.CHATBOT.value, cls.CHATBOT.value),
            (cls.PROVIDER.value, cls.PROVIDER.value),
            (cls.SECRET.value, cls.SECRET.value),
        ]


class SmarterJournalCliCommands(SmarterEnumAbstract):
    """
    Enumerates the available commands for ``api/v1/cli`` requests.

    This class inherits from :class:`SmarterEnumAbstract`, which is typically implemented as a subclassed Singleton.
    For flexibility, it also allows instantiation with a string value, enabling a ``SmarterJournalCliCommands`` value
    to be passed as a strongly typed object.

    Each member represents a supported CLI command in the Smarter API, such as ``apply``, ``chat``, ``delete``, ``deploy``, etc.

    Example usage::

        command = SmarterJournalCliCommands("apply")
        assert command == SmarterJournalCliCommands.APPLY

    """

    APPLY = "apply"
    CHAT = "chat"
    CHAT_CONFIG = "chat_config"
    DELETE = "delete"
    DEPLOY = "deploy"
    DESCRIBE = "describe"
    GET = "get"
    JOURNAL = "journal"  # FIXNOTE: THIS IS AMBIGUOUS
    LOGS = "logs"  # FIXNOTE: THIS IS AMBIGUOUS
    MANIFEST_EXAMPLE = "example_manifest"
    STATUS = "status"
    SCHEMA = "schema"
    VERSION = "version"
    UNDEPLOY = "undeploy"
    WHOAMI = "whoami"

    @classmethod
    def choices(cls) -> list[tuple[str, str]]:
        """Django model choices for SmarterJournalCliCommands."""
        return [
            (cls.APPLY.value, cls.APPLY.value),
            (cls.CHAT.value, cls.CHAT.value),
            (cls.CHAT_CONFIG.value, cls.CHAT_CONFIG.value),
            (cls.DELETE.value, cls.DELETE.value),
            (cls.DEPLOY.value, cls.DEPLOY.value),
            (cls.DESCRIBE.value, cls.DESCRIBE.value),
            (cls.GET.value, cls.GET.value),
            (cls.JOURNAL.value, cls.JOURNAL.value),
            (cls.LOGS.value, cls.LOGS.value),
            (cls.MANIFEST_EXAMPLE.value, cls.MANIFEST_EXAMPLE.value),
            (cls.STATUS.value, cls.STATUS.value),
            (cls.SCHEMA.value, cls.SCHEMA.value),
            (cls.VERSION.value, cls.VERSION.value),
            (cls.UNDEPLOY.value, cls.UNDEPLOY.value),
            (cls.WHOAMI.value, cls.WHOAMI.value),
        ]

    @classmethod
    def past_tense(cls) -> dict[str, str]:
        """Return the past tense of the command."""
        return {
            cls.APPLY.value: "applied",
            cls.CHAT.value: "prompted",
            cls.CHAT_CONFIG.value: "fetched chat_config",
            cls.DELETE.value: "deleted",
            cls.DEPLOY.value: "deployed",
            cls.DESCRIBE.value: "described",
            cls.GET.value: "got",
            cls.JOURNAL.value: "journaled",
            cls.LOGS.value: "logged",
            cls.MANIFEST_EXAMPLE.value: "fetched example manifest",
            cls.STATUS.value: "fetched status",
            cls.SCHEMA.value: "fetched schema",
            cls.VERSION.value: "fetched version",
            cls.UNDEPLOY.value: "undeployed",
            cls.WHOAMI.value: "fetched identity",
        }

    @classmethod
    def from_url(cls, url) -> Optional[str]:
        """
        Parse a url and return the SmarterJournalCliCommands enum value
        if it exists in the url path.
        example: http://localhost:8000/api/v1/cli/example_manifest/Account/
        """
        parsed_url = urlparse(url)
        if parsed_url:
            slugs = parsed_url.path.split("/")
            if not "api" in slugs:
                return None
            for slug in slugs:
                this_slug = str(slug).lower()
                if this_slug in cls.all_values():
                    return this_slug
        logger.warning("SmarterJournalCliCommands.from_url() could not extract manifest kind from URL: %s", url)
