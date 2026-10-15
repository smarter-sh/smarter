"""Smarter Extension exceptions."""

from smarter.common.exceptions import SmarterException


class SmarterExtensionException(SmarterException):
    """Base class for all Smarter Extension exceptions."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Extension error"


class SmarterExtensionManifestError(SmarterExtensionException):
    """An extension's ``pyproject.toml`` is missing, or is not a valid extension manifest."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Extension manifest error"


class SmarterExtensionArchiveError(SmarterExtensionException):
    """An extension archive is not a valid zip file, is too large, or is laid out incorrectly."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Extension archive error"


class SmarterExtensionInstallError(SmarterExtensionException):
    """An extension cannot be installed, updated or enabled, e.g. because it is incompatible with this platform."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Extension install error"


class SmarterExtensionLoadError(SmarterExtensionException):
    """An installed extension's code could not be imported, or its tools are not valid."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Extension load error"


class SmarterExtensionRegistryError(SmarterExtensionException):
    """The extension registry could not be reached, or its index is not valid or not authentic."""

    @property
    def get_formatted_err_message(self):
        return "Smarter Extension registry error"


__all__ = [
    "SmarterExtensionArchiveError",
    "SmarterExtensionException",
    "SmarterExtensionInstallError",
    "SmarterExtensionLoadError",
    "SmarterExtensionManifestError",
    "SmarterExtensionRegistryError",
]
