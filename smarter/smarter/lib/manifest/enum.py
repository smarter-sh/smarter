"""Smarter API Manifests Enumerations."""

from smarter.common.enum import SmarterEnumAbstract

from .exceptions import SAMExceptionBase


class SAMEnumException(SAMExceptionBase):
    """Base exception for Smarter API Manifest enumerations."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Manifest Enumeration Error"


###############################################################################
# Smarter API Manifest Enumerations
###############################################################################


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

    ACCOUNT = "account"
    AUTHOR = "author"
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
