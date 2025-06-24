"""
This module is intended to future-proof the Smarter User object.
"""

from typing import TYPE_CHECKING, Optional, Union

from django.contrib.auth import get_user_model
from django.contrib.auth.models import AbstractUser, AnonymousUser
from django.contrib.auth.models import User as DjangoUser
from django.utils.functional import SimpleLazyObject

from smarter.common.exceptions import SmarterConfigurationError


User = get_user_model()
User = User if issubclass(User, DjangoUser) else None
if User is None:
    raise SmarterConfigurationError("Django User model is not available. Ensure Django is properly configured.")
UserClass = DjangoUser

if TYPE_CHECKING:
    from django.contrib.auth.models import _AnyUser


def get_resolved_user(
    user: "Union[DjangoUser, AbstractUser, AnonymousUser, SimpleLazyObject, _AnyUser]",
) -> Optional[Union[DjangoUser, AnonymousUser]]:
    """
    Get the resolved user object from a user instance.
    Maps the various kinds of Django user subclasses and mutations to the UserClass.
    Used for resolving type annotations and ensuring type safety.
    """
    # pylint: disable=W0212
    if isinstance(user, SimpleLazyObject):
        return user._wrapped
    if isinstance(user, AnonymousUser):
        return user
    if isinstance(user, DjangoUser):
        return user
    raise SmarterConfigurationError(
        f"Unexpected user type: {type(user)}. Expected Django User, AnonymousUser, or SimpleLazyObject."
    )
