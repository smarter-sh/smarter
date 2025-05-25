"""
Abstract helper class to map a manifest model's metadata.kindClass to an
instance of the the correct Python subclass.
"""

import abc
from typing import Any

from smarter.apps.account.mixins import AccountMixin
from smarter.lib.manifest.models import AbstractSAMBase


class AbstractController(abc.ABC, AccountMixin):
    """Map the Pydantic metadata.kindClass to the corresponding object instance."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        AccountMixin.__init__(self, *args, **kwargs)

    ###########################################################################
    # Abstract property implementations
    ###########################################################################
    @property
    @abc.abstractmethod
    def manifest(self) -> AbstractSAMBase:
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def map(self):
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def obj(self) -> Any:
        raise NotImplementedError
