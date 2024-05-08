"""
Abstract helper class to map a manifest model's metadata.kindClass to an
instance of the the correct Python subclass.
"""

import abc
from typing import Any

from smarter.apps.api.v1.manifests.models import AbstractSAMBase


class AbstractController(abc.ABC):
    """Map the Pydantic metadata.kindClass to the corresponding object instance."""

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
