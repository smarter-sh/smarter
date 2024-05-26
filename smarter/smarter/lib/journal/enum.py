"""Smarter API Manifests Enumerations."""

from smarter.common.exceptions import SmarterExceptionBase


class SmarterJournalEnumException(SmarterExceptionBase):
    """Base exception for Smarter API Manifest enumerations."""

    @property
    def get_readable_name(self):
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


class SCLIResponseMetadata:
    """CLI get response metadata enumeration."""

    KEY = "key"


class SmarterJounalDjangoModelBase:
    """Base class for Smarter API cli enumerations that are used in Django models as choices."""

    # vanity method added so that this class can be used in Django model choices
    # without it appearing confusing. example:
    #   command = models.CharField(max_length=64, choices=SmarterJournalCliCommands.choices())
    @classmethod
    def choices(cls) -> list[str]:
        return cls.all_values()


class SmarterJournalThings(SmarterJounalDjangoModelBase):
    """
    Smarter api cli things that can be added to the Journal. This descends
    from SmarterEnumAbstract which is generally implemented as a subclassed
    Singleton. For the avoidance of any doubt, we're doing here as well, but
    we're also allowing this to be instantiated with a string value, so that
    a SmarterJournalThings value can passed as a strongly typed object.
    """

    PLUGIN = "plugin"
    ACCOUNT = "account"
    APIKEY = "apikey"
    USER = "user"
    CHAT = "chat"
    CHAT_HISTORY = "chat_history"
    CHAT_PLUGIN_USAGE = "chat_plugin_usage"
    CHAT_TOOL_CALL = "chat_tool_call"
    CHATBOT = "chatbot"
    SQLCONNECTION = "sqlconnection"
    APICONNECTION = "apiconnection"

    _thing: str = None

    def __init__(self, thing: str = None) -> None:
        thing = str(thing).lower()
        if thing not in self.all_values():
            raise SmarterJournalEnumException(
                f"Invalid Smarter Journal thing: {thing}. Valid things are: {self.all_values()}"
            )
        self._thing = thing
        super().__init__()

    @property
    def value(self) -> str:
        return self._thing

    def __str__(self) -> str:
        return self._thing


class SmarterJournalCliCommands(SmarterJounalDjangoModelBase):
    """
    Enumerated commands for api/v1/cli requests. This descends
    from SmarterEnumAbstract which is generally implemented as a subclassed
    Singleton. For the avoidance of any doubt, we're doing here as well, but
    we're also allowing this to be instantiated with a string value, so that
    a SmarterJournalCliCommands value can passed as a strongly typed object.
    """

    APPLY = "apply"
    CHAT = "chat"
    DELETE = "delete"
    DEPLOY = "deploy"
    DESCRIBE = "describe"
    GET = "get"
    JOURNAL = "journal"  # FIXNOTE: THIS IS AMBIGUOUS
    LOGS = "logs"  # FIXNOTE: THIS IS AMBIGUOUS
    MANIFEST_EXAMPLE = "example_manifest"
    STATUS = "status"
    VERSION = "version"
    UNDEPLOY = "undeploy"
    WHOAMI = "whoami"

    _command: str = None

    @classmethod
    def past_tense(cls) -> dict:
        return {
            cls.APPLY: "applied",
            cls.CHAT: "chatted",
            cls.DELETE: "deleted",
            cls.DEPLOY: "deployed",
            cls.DESCRIBE: "described",
            cls.GET: "got",
            cls.JOURNAL: "journaled",
            cls.LOGS: "retrieved logs",
            cls.MANIFEST_EXAMPLE: "got example manifest",
            cls.STATUS: "got status",
            cls.VERSION: "got version",
            cls.UNDEPLOY: "undeployed",
            cls.WHOAMI: "user account identified",
        }

    def __init__(self, kind: str = None) -> None:
        if kind not in self.all_values():
            raise SmarterJournalEnumException(
                f"Invalid Smarter Journal command: {kind}. Valid commands are: {self.all_values()}"
            )
        self._command = kind
        super().__init__()

    @property
    def value(self) -> str:
        return self._thing

    def __str__(self) -> str:
        return self._command
