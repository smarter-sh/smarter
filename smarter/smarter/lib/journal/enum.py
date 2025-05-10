"""Smarter API Manifests Enumerations."""

import logging
from urllib.parse import urlparse

from smarter.common.enum import SmarterEnumAbstract
from smarter.common.exceptions import SmarterExceptionBase


logger = logging.getLogger(__name__)


class SmarterJournalEnumException(SmarterExceptionBase):
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
    Smarter api cli things that can be added to the Journal. This descends
    from SmarterEnumAbstract which is generally implemented as a subclassed
    Singleton. For the avoidance of any doubt, we're doing here as well, but
    we're also allowing this to be instantiated with a string value, so that
    a SmarterJournalThings value can passed as a strongly typed object.
    """

    STATIC_PLUGIN = "Plugin"
    API_PLUGIN = "ApiPlugin"
    SQL_PLUGIN = "SqlPlugin"
    API_CONNECTION = "ApiConnection"
    SQL_CONNECTION = "SqlConnection"
    ACCOUNT = "Account"
    APIKEY = "SmarterAuthToken"
    USER = "User"
    CHAT = "Chat"
    CHAT_CONFIG = "ChatConfig"
    CHAT_HISTORY = "ChatHistory"
    CHAT_PLUGIN_USAGE = "ChatPluginUsage"
    CHAT_TOOL_CALL = "ChatToolCall"
    CHATBOT = "Chatbot"
    SECRET = "Secret"

    @classmethod
    def choices(cls) -> list[(str, str)]:
        """Django model choices for SmarterJournalThings."""
        return [
            (cls.STATIC_PLUGIN, cls.STATIC_PLUGIN),
            (cls.API_PLUGIN, cls.API_PLUGIN),
            (cls.SQL_PLUGIN, cls.SQL_PLUGIN),
            (cls.API_CONNECTION, cls.API_CONNECTION),
            (cls.SQL_CONNECTION, cls.SQL_CONNECTION),
            (cls.ACCOUNT, cls.ACCOUNT),
            (cls.APIKEY, cls.APIKEY),
            (cls.USER, cls.USER),
            (cls.CHAT, cls.CHAT),
            (cls.CHAT_CONFIG, cls.CHAT_CONFIG),
            (cls.CHAT_HISTORY, cls.CHAT_HISTORY),
            (cls.CHAT_PLUGIN_USAGE, cls.CHAT_PLUGIN_USAGE),
            (cls.CHAT_TOOL_CALL, cls.CHAT_TOOL_CALL),
            (cls.CHATBOT, cls.CHATBOT),
            (cls.SECRET, cls.SECRET),
        ]


class SmarterJournalCliCommands(SmarterEnumAbstract):
    """
    Enumerated commands for api/v1/cli requests. This descends
    from SmarterEnumAbstract which is generally implemented as a subclassed
    Singleton. For the avoidance of any doubt, we're doing here as well, but
    we're also allowing this to be instantiated with a string value, so that
    a SmarterJournalCliCommands value can passed as a strongly typed object.
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
    def choices(cls) -> list[(str, str)]:
        """Django model choices for SmarterJournalCliCommands."""
        return [
            (cls.APPLY, cls.APPLY),
            (cls.CHAT, cls.CHAT),
            (cls.CHAT_CONFIG, cls.CHAT_CONFIG),
            (cls.DELETE, cls.DELETE),
            (cls.DEPLOY, cls.DEPLOY),
            (cls.DESCRIBE, cls.DESCRIBE),
            (cls.GET, cls.GET),
            (cls.JOURNAL, cls.JOURNAL),
            (cls.LOGS, cls.LOGS),
            (cls.MANIFEST_EXAMPLE, cls.MANIFEST_EXAMPLE),
            (cls.STATUS, cls.STATUS),
            (cls.SCHEMA, cls.SCHEMA),
            (cls.VERSION, cls.VERSION),
            (cls.UNDEPLOY, cls.UNDEPLOY),
            (cls.WHOAMI, cls.WHOAMI),
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
    def from_url(cls, url) -> str:
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
