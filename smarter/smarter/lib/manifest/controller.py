"""
Abstract helper class to map a manifest model's metadata.kindClass to an
instance of the the correct Python subclass.
"""

import abc
from typing import Any

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account
from smarter.lib.django.user import UserType
from smarter.lib.manifest.models import AbstractSAMBase


class AbstractController(abc.ABC, AccountMixin):
    """Map the Pydantic metadata.kindClass to the corresponding object instance."""

    def __init__(self, account: Account, user: UserType, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_profile = kwargs.pop("user_profile", None)
        AccountMixin.__init__(self, account=account, user=user, user_profile=user_profile, *args, **kwargs)

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
