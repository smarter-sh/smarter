"""Smarter API V0 Manifests Enumerations."""

from enum import Enum


class SmarterEnumAbstract(Enum):
    """Smarter enumeration helper class."""

    @classmethod
    def all_values(cls) -> list[str]:
        return [member.value for _, member in cls.__members__.items()]


class DbEngine(SmarterEnumAbstract):
    """SQL database engine enumeration."""

    POSTGRES = "postgres"
    MYSQL = "mysql"
    ORACLE = "oracle"
    SQLITE = "sqlite"
    MSSQL = "mssql"


class SAMDataFormats(SmarterEnumAbstract):
    """Data format enumeration."""

    JSON = "json"
    YAML = "yaml"


class SAMSpecificationKeyOptions(SmarterEnumAbstract):
    """Key types enumeration."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    READONLY = "readonly"


class SAMKinds(SmarterEnumAbstract):
    """Smarter manifest kinds enumeration."""

    PLUGIN = "Plugin"
    ACCOUNT = "Account"
    USER = "User"
    CHAT = "Chat"
    CHATBOT = "Chatbot"


class SAMKeys(SmarterEnumAbstract):
    """Smarter API V0 required keys enumeration."""

    APIVERSION = "apiVersion"
    KIND = "kind"
    METADATA = "metadata"
    SPEC = "spec"
    STATUS = "status"


class SAMMetadataKeys(SmarterEnumAbstract):
    """Smarter API V0 Plugin Metadata keys enumeration."""

    NAME = "name"
    ACCOUNT_NUMBER = "accountNumber"
    DESCRIPTION = "description"
    VERSION = "version"
    TAGS = "tags"
    ANNOTATIONS = "annotations"
