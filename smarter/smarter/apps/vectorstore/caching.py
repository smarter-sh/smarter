# pylint: disable=W0613,W0212
"""
Cached querysets of the vectorstores that a user may see: those they own, those shared with.

them, and both. A vectorstore's post_save and post_delete receivers invalidate its owner's.
"""

from django.db import models

from smarter.apps.account.models.user_profile import UserProfile
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .models import VectorstoreMeta

logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.VECTORSTORE_LOGGING, SmarterWaffleSwitches.CACHE_LOGGING]
)


@cache_results()
def _get_cached_vectorstores_owned_by_user_profile(user_profile_id: int) -> models.QuerySet[VectorstoreMeta]:
    user_profile = UserProfile.objects.get(id=user_profile_id)
    return VectorstoreMeta.objects.owned_by(user_profile.user)  # type: ignore


@cache_results()
def _get_cached_vectorstores_shared_with_user_profile(user_profile_id: int) -> models.QuerySet[VectorstoreMeta]:
    user_profile = UserProfile.objects.get(id=user_profile_id)
    return VectorstoreMeta.objects.shared_with(user_profile.user)  # type: ignore


@cache_results()
def _get_cached_vectorstores_available_to_user_profile(user_profile_id: int) -> models.QuerySet[VectorstoreMeta]:
    user_profile = UserProfile.objects.get(id=user_profile_id)
    return VectorstoreMeta.objects.with_read_permission_for(user_profile.user)  # type: ignore


def get_cached_vectorstores_owned_by_user_profile(user_profile: UserProfile) -> models.QuerySet[VectorstoreMeta]:
    """The vectorstores that the user owns."""
    return _get_cached_vectorstores_owned_by_user_profile(user_profile.id)  # type: ignore


def get_cached_vectorstores_shared_with_user_profile(user_profile: UserProfile) -> models.QuerySet[VectorstoreMeta]:
    """The vectorstores shared with the user: their account's, and the platform's."""
    return _get_cached_vectorstores_shared_with_user_profile(user_profile.id)  # type: ignore


def get_cached_vectorstores_available_to_user_profile(user_profile: UserProfile) -> models.QuerySet[VectorstoreMeta]:
    """The vectorstores that the user may read: owned and shared."""
    return _get_cached_vectorstores_available_to_user_profile(user_profile.id)  # type: ignore


def invalidate_all_cached_vectorstores_for_user_profile(user_profile: UserProfile) -> None:
    """Invalidate the user's cached vectorstores."""
    _get_cached_vectorstores_owned_by_user_profile.invalidate(user_profile.id)  # type: ignore
    _get_cached_vectorstores_shared_with_user_profile.invalidate(user_profile.id)  # type: ignore
    _get_cached_vectorstores_available_to_user_profile.invalidate(user_profile.id)  # type: ignore
    logger.debug("%s invalidated the vectorstores of %s", logging.formatted_text(__name__), user_profile)


__all__ = [
    "get_cached_vectorstores_available_to_user_profile",
    "get_cached_vectorstores_owned_by_user_profile",
    "get_cached_vectorstores_shared_with_user_profile",
    "invalidate_all_cached_vectorstores_for_user_profile",
]
