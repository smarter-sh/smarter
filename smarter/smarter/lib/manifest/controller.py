"""
Abstract helper class to map a manifest model's metadata.kindClass to an
instance of the the correct Python subclass.
"""

import abc
import typing
from typing import Any

from smarter.lib.manifest.models import AbstractSAMBase


if typing.TYPE_CHECKING:
    from smarter.apps.account.models import Account


class AbstractController(abc.ABC):
    """Map the Pydantic metadata.kindClass to the corresponding object instance."""

    _account: "Account" = None

    ###########################################################################
    # Abstract property implementations
    ###########################################################################
    @property
    def account(self) -> "Account":
        return self._account

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
