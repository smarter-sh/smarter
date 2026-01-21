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
    """
    Data format enumeration.

    .. :no-index:

    Used to specify the format of data being handled, such as JSON or YAML.

    attributes:
        JSON: Represents data in JSON format.
        YAML: Represents data in YAML format.
        UNKNOWN: Represents an unknown or unsupported data format.
    """

    JSON = "json"
    YAML = "yaml"
    UNKNOWN = "unknown"


class SAMSpecificationKeyOptions(SmarterEnumAbstract):
    """
    Key types enumeration.
    Used to specify whether a key in the specification is required, optional, or read-only.

    .. :no-index:

    attributes:
        REQUIRED: Indicates that the key is mandatory.
        OPTIONAL: Indicates that the key is optional.
        READONLY: Indicates that the key is read-only and cannot be modified.
    """

    REQUIRED = "required"
    OPTIONAL = "optional"
    READONLY = "readonly"


class SAMKeys(SmarterEnumAbstract):
    """
    Smarter API required keys enumeration.

    .. :no-index:

    attributes:
        APIVERSION: The API version key.
        KIND: The kind key.
        METADATA: The metadata key.
        SPEC: The specification key.
        STATUS: The status key.
    """

    APIVERSION = "apiVersion"
    KIND = "kind"
    METADATA = "metadata"
    SPEC = "spec"
    STATUS = "status"


class SAMMetadataKeys(SmarterEnumAbstract):
    """
    Smarter API Plugin Metadata keys enumeration.

    .. :no-index:

    attributes:
        ACCOUNT: The account key.
        AUTHOR: The author key.
        NAME: The name key.
        DESCRIPTION: The description key.
        VERSION: The version key.
        TAGS: The tags key.
        ANNOTATIONS: The annotations key.
    """

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
    """
    CLI get response enumeration.

    .. :no-index:

    attributes:
        KWARGS: The kwargs key.
        DATA: The data key.
    """

    KWARGS = "kwargs"
    DATA = "data"


class SCLIResponseGetData(SmarterEnumAbstract):
    """

    CLI get response data enumeration.

    .. :no-index:

    attributes:
        TITLES: The titles key.
        ITEMS: The items key.
    """

    TITLES = "titles"
    ITEMS = "items"
