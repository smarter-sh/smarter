"""Abstract helper class that maps a manifest model's metadata.kindClass to an instance of the correct Python subclass."""

import abc
from collections.abc import Mapping
from typing import Any

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib.manifest.models import AbstractSAMBase


class AbstractController(abc.ABC, AccountMixin):
    """
    Abstract base class for mapping a manifest model's ``metadata.kindClass`` to the correct Python object instance.

    This controller is designed to facilitate the instantiation and management of objects based on manifest metadata,
    ensuring that the correct subclass is used for each manifest type. It also provides account and user context
    through the ``AccountMixin``.

    :param user_profile: The user profile that owns the controlled resource. Its account and user
        are the controller's account and user.
    :param args: Passed on to :class:`~smarter.apps.account.mixins.AccountMixin`.
    :param kwargs: Passed on to :class:`~smarter.apps.account.mixins.AccountMixin`, e.g. ``request``.

    **Usage Example:**

    .. code-block:: python

        user_profile = UserProfile.get_cached_object(user=user)
        controller = MyControllerSubclass(user_profile, request=request)

        # Access manifest, map, and obj properties
        manifest = controller.manifest
        mapping = controller.map
        obj_instance = controller.obj

    .. note::

        This class is abstract and must be subclassed with concrete implementations of the ``manifest``, ``map``, and ``obj`` properties.

    .. warning::

        A subclass that does not implement all of the abstract properties cannot be instantiated.
    """

    def __init__(self, user_profile: UserProfile, *args: Any, **kwargs: Any) -> None:
        """
        Initialize the account context from the user profile, with one AccountMixin initialization.

        :param user_profile: The user profile that owns the controlled resource.
        :param args: Passed on to :class:`~smarter.apps.account.mixins.AccountMixin`.
        :param kwargs: Passed on to :class:`~smarter.apps.account.mixins.AccountMixin`.
        """
        # One AccountMixin initialization. (abc.ABC has no __init__, so super() is AccountMixin.)
        # It used to run twice: once without the user profile, and then again with it, which
        # resets and resolves everything the first run did. The cached accessors read the
        # profile's account and user from the cache rather than with a query.
        super().__init__(
            *args,
            account=user_profile.cached_account,
            user=user_profile.cached_user,
            user_profile=user_profile,
            **kwargs,
        )

    ###########################################################################
    # Abstract property implementations
    ###########################################################################
    @property
    @abc.abstractmethod
    def manifest(self) -> AbstractSAMBase:
        """The Pydantic manifest of the controlled resource; subclasses implement it."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def map(self) -> Mapping[str, Any]:
        """The mapping from manifest kinds to the classes that handle them; subclasses implement it."""
        raise NotImplementedError

    @property
    @abc.abstractmethod
    def obj(self) -> Any:
        """The object that handles the manifest's kind, from :attr:`map`; subclasses implement it."""
        raise NotImplementedError
