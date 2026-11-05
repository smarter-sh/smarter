"""Smarter API Manifests Enumerations."""

from smarter.common.enum import SmarterEnumAbstract

from .exceptions import SAMExceptionBase


class SAMEnumException(SAMExceptionBase):
    """Base exception for Smarter API Manifest enumerations."""

    @property
    def get_formatted_err_message(self) -> str:
        """The error message prefix of these errors."""
        return "Smarter API Manifest Enumeration Error"


###############################################################################
# Smarter API Manifest Enumerations
###############################################################################


class SAMDataFormats(SmarterEnumAbstract):
    """
    Data format enumeration.

    Used to specify the format of data being handled, such as JSON or YAML.
    """

    #: Data in JSON format.
    JSON = "json"
    #: Data in YAML format.
    YAML = "yaml"
    #: An unknown or unsupported data format.
    UNKNOWN = "unknown"


class SAMSpecificationKeyOptions(SmarterEnumAbstract):
    """
    Key types enumeration.

    Used to specify whether a key in the specification is required, optional, or read-only.
    """

    #: The key is mandatory.
    REQUIRED = "required"
    #: The key is optional.
    OPTIONAL = "optional"
    #: The key is read-only and cannot be modified.
    READONLY = "readonly"


class SAMKeys(SmarterEnumAbstract):
    """Smarter API Manifest top-level keys enumeration."""

    #: The API version key.
    APIVERSION = "apiVersion"
    #: The kind key.
    KIND = "kind"
    #: The metadata key.
    METADATA = "metadata"
    #: The specification key.
    SPEC = "spec"
    #: The status key.
    STATUS = "status"


class SAMMetadataKeys(SmarterEnumAbstract):
    """Smarter API Manifest metadata keys enumeration."""

    #: The author key.
    AUTHOR = "author"
    #: The name key.
    NAME = "name"
    #: The description key.
    DESCRIPTION = "description"
    #: The version key.
    VERSION = "version"
    #: The tags key.
    TAGS = "tags"
    #: The annotations key.
    ANNOTATIONS = "annotations"


###############################################################################
# Smarter API cli response Enumerations
###############################################################################
class SCLIResponseGet(SmarterEnumAbstract):
    """CLI get response enumeration."""

    #: The kwargs key.
    KWARGS = "kwargs"
    #: The data key.
    DATA = "data"


class SCLIResponseGetData(SmarterEnumAbstract):
    """CLI get response data enumeration."""

    #: The titles key.
    TITLES = "titles"
    #: The items key.
    ITEMS = "items"
