"""
Abstract helper class to map a manifest model's metadata.kindClass to an
instance of the the correct Python subclass.
"""

import abc
from typing import Any

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account, User
from smarter.lib.manifest.models import AbstractSAMBase


class AbstractController(abc.ABC, AccountMixin):
    """
    Abstract base class for mapping a manifest model's `metadata.kindClass` to the correct Python object instance.

    This controller is designed to facilitate the instantiation and management of objects based on manifest metadata,
    ensuring that the correct subclass is used for each manifest type. It also provides account and user context
    through the `AccountMixin`.

    **Parameters:**
        account (Account): The account associated with the controller instance. Must be a saved model.
        user (User): The user associated with the controller instance. Must be a saved model.
        user_profile (optional): The user's profile, if available.
        request (optional): The request object, if available.
        *args, **kwargs: Additional arguments passed to the mixin and controller.

    **Usage Example:**

        .. code-block:: python

            account = Account.objects.get(pk=1)
            user = User.objects.get(pk=1)
            controller = MyControllerSubclass(account, user, user_profile=profile, request=request)

            # Access manifest, map, and obj properties
            manifest = controller.manifest
            mapping = controller.map
            obj_instance = controller.obj

    .. note::

        - Both `account` and `user` must be saved instances (i.e., have a primary key).
        - This class is abstract and must be subclassed with concrete implementations of the `manifest`, `map`, and `obj` properties.

    .. warning::

        - Attempting to instantiate this controller with unsaved `account` or `user` objects will raise a `ValueError`.
        - Subclasses must implement all abstract properties, or a `NotImplementedError` will be raised.

    """

    def __init__(self, account: Account, user: User, *args, **kwargs):
        super().__init__(*args, **kwargs)
        user_profile = kwargs.pop("user_profile", None)
        request = kwargs.pop("request", None)
        if not account.pk or not user.pk:
            raise ValueError("unsaved data was padded to the controller")
        AccountMixin.__init__(
            self, account=account, user=user, user_profile=user_profile, request=request, *args, **kwargs
        )

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
