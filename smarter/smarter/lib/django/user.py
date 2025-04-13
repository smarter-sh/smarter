"""This module is intended to future-proof the Smarter User object."""

from typing import Type

from django.contrib.auth import get_user_model
from django.utils.functional import SimpleLazyObject


User = get_user_model()
UserType = Type[User]


def get_resolved_user(user: UserType) -> UserType:
    """
    Get the resolved user object from a SimpleLazyObject or return the user directly.
    """
    # pylint: disable=W0212
    if isinstance(user, SimpleLazyObject):
        return user._wrapped
    return user
