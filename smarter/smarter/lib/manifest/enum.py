"""Smarter API Manifests Enumerations."""

from enum import Enum


VERSION_PREFIX = "smarter.sh"


class SmarterEnumAbstract(Enum):
    """Smarter enumeration helper class."""

    @classmethod
    def all_values(cls) -> list[str]:
        return [member.value for _, member in cls.__members__.items()]


###############################################################################
# Smarter API Manifest Enumerations
###############################################################################
class SAMApiVersions(SmarterEnumAbstract):
    """API Version enumeration."""

    V0 = f"{VERSION_PREFIX}/v0"
    V1 = f"{VERSION_PREFIX}/v1"


class SAMDataFormats(SmarterEnumAbstract):
    """Data format enumeration."""

    JSON = "json"
    YAML = "yaml"


class SAMSpecificationKeyOptions(SmarterEnumAbstract):
    """Key types enumeration."""

    REQUIRED = "required"
    OPTIONAL = "optional"
    READONLY = "readonly"


class SAMKeys(SmarterEnumAbstract):
    """Smarter API required keys enumeration."""

    APIVERSION = "apiVersion"
    KIND = "kind"
    METADATA = "metadata"
    SPEC = "spec"
    STATUS = "status"


class SAMMetadataKeys(SmarterEnumAbstract):
    """Smarter API Plugin Metadata keys enumeration."""

    NAME = "name"
    DESCRIPTION = "description"
    VERSION = "version"
    TAGS = "tags"
    ANNOTATIONS = "annotations"


###############################################################################
# Smarter API cli response Enumerations
###############################################################################
class SCLIResponseGet(SmarterEnumAbstract):
    """CLI get response enumeration."""

    KWARGS = "kwargs"
    DATA = "data"


class SCLIResponseGetData(SmarterEnumAbstract):
    """CLI get response data enumeration."""

    TITLES = "titles"
    ITEMS = "items"
