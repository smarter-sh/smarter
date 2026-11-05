"""
Cache management for API keys, the :class:`~smarter.lib.drf.models.SmarterAuthToken` model.

A user's API keys are cached by :func:`smarter.lib.drf.models.cached_auth_tokens`, and the
cache is invalidated whenever an API key is saved or deleted. :func:`invalidate_all_cached_authtokens_for_user_profile`
also drops it explicitly, e.g. after a list view changed a key.
"""

from smarter.apps.account.models.user_profile import UserProfile

from .models import invalidate_cached_auth_tokens


def invalidate_all_cached_authtokens_for_user_profile(user_profile: UserProfile) -> None:
    """
    Drop the cached API keys of a user profile's user, for every profile of the user.

    :param user_profile: The user profile whose user's API keys changed.
    """
    invalidate_cached_auth_tokens(user_profile.user_id, names=())


__all__ = ["invalidate_all_cached_authtokens_for_user_profile"]
