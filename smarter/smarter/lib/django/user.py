"""This module is intended to future-proof the Smarter User object."""

from typing import Optional, Type, Union

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.utils.functional import SimpleLazyObject


User = get_user_model()
UserClass = Type[User]


def get_resolved_user(user: Union[User, AbstractUser, AnonymousUser, SimpleLazyObject]) -> Optional[User]:
    """
    Get the resolved user object from a SimpleLazyObject or return the user directly.
    """
    # pylint: disable=W0212
    if isinstance(user, SimpleLazyObject):
        return user._wrapped
    return user if isinstance(user, User) else None
