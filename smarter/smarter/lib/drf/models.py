"""DRF knox authtoken model and manager."""

import hmac
import uuid
from collections.abc import Iterable
from datetime import datetime, timedelta
from logging import getLogger
from typing import Optional

from cache_results import cache_results
from django.db import models
from django.urls import reverse
from django.utils import timezone
from knox import crypto
from knox.models import AuthToken
from knox.settings import CONSTANTS

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    MetaDataWithOwnershipModelManager,
    User,
    UserProfile,
)
from smarter.common.exceptions import SmarterBusinessRuleViolation, SmarterValueError
from smarter.common.helpers.console_helpers import SmarterFormattedText
from smarter.common.utils import to_snake_case
from smarter.lib.django.validators import SmarterValidator

logger = getLogger(__name__)
logger_prefix = SmarterFormattedText.text(__name__)

###############################################################################
# API Key Management
###############################################################################


LAST_USED_RESOLUTION = timedelta(minutes=1)
"""
How precisely an api key's ``last_used_at`` is kept.

Every authenticated request uses its key, so ``last_used_at`` is written at most once per
this interval per key, not on every request.
"""


class SmarterAuthTokenManager(MetaDataWithOwnershipModelManager["SmarterAuthToken"]):
    """
    Manager of API keys, which creates them as knox's ``AuthTokenManager`` does.

    It is derived from Smarter's ``MetaDataWithOwnershipModelManager``, for Smarter's
    permission-based querying, and adds a ``create()`` that generates the token as knox does.
    """

    # knox's AuthTokenManager.create() takes the owner and returns the row with its plain token,
    # so the override is intended.
    def create(  # type: ignore[override]
        self,
        user: User,
        expiry=None,
        prefix=None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        **kwargs,
    ) -> tuple["SmarterAuthToken", str]:
        """
        Create and save a new API key for a user.

        Only the token's digest is stored; the token itself is returned once, here.

        :param user: The user who owns the key; must be staff.
        :param expiry: How long the key is valid, as a timedelta, or None for no expiry.
        :param prefix: An optional prefix for the token string.
        :param name: The key's name.
        :param description: The key's description.
        :param is_active: Whether the key is active.
        :param kwargs: More model fields.
        :returns: A tuple of the saved key and the plain token.
        :raises SmarterBusinessRuleViolation: If the user is not staff.
        :raises SmarterValueError: If ``name`` is None.
        """
        if name is None:
            raise SmarterValueError("An API key needs a name.")
        prefix = prefix or ""
        token = prefix + crypto.create_token_string()
        token_key = token[: CONSTANTS.TOKEN_KEY_LENGTH]
        digest = crypto.hash_token(token)
        if expiry is not None:
            expiry = timezone.now() + expiry

        auth_token = self.model(
            token_key=token_key,
            digest=digest,
            user=user,
            expiry=expiry,
            name=name,
            description=description,
            is_active=is_active,
            **kwargs,
        )
        auth_token.save()
        # never log token_key: it is the first characters of the token itself.
        logger.info(
            "%s.SmarterAuthTokenManager.create() created API key %s (%s) for user %s, expiring %s",
            logger_prefix,
            auth_token.name,
            auth_token.key_id,
            user,
            expiry,
        )
        return auth_token, token


class SmarterAuthToken(AuthToken, MetaDataWithOwnershipModel):
    """
    Represents a Smarter API Key used for authenticating and authorizing access to the Smarter platform.

    This model extends Knox's ``AuthToken`` and includes additional metadata and management features
    for API keys, such as naming, description, activation status, and usage tracking.

    **Fields:**

    - ``key_id``: The API key's unique, public identifier.
    - ``name``: The API key's human-readable name, in snake_case.
    - ``description``: An optional description of the API key's purpose.
    - ``last_used_at``: When the API key was last used, to within :data:`LAST_USED_RESOLUTION`.
    - ``is_active``: Whether the API key can be used for authentication.
    - ``tags``: A list of tag names.

    **Usage Example:**

        .. code-block:: python

            # Creating an API key for a staff user
            user = User.objects.get(username="admin")
            token, key = SmarterAuthToken.objects.create(
                user=user,
                name="Production Key",
                description="Key for production API access"
            )

            # Activating or deactivating the key
            token.activate()
            token.deactivate()

            # Toggling active status
            token.toggle_active()

            # Tracking usage
            token.accessed()

    .. note::

        - API keys can only be created for staff users. Attempting to create a key for a non-staff user
          will raise a ``SmarterBusinessRuleViolation``.
        - The ``identifier`` property returns a masked version of the key digest for display purposes.
        - Names are stored in snake_case, as every SAM manifest name is, so that ``get`` and
          ``describe`` report the same name. ``save()`` converts any other name.

    .. warning::

        - Ensure that API keys are managed securely. Deactivated keys cannot be used for authentication.

    **Related Models:**

    - ``User``: The owner of the API key.
    - ``MetaDataModel``: Provides created/modified timestamps and SAM metadata.
    """

    objects = SmarterAuthTokenManager()

    # pylint: disable=C0115
    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    key_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)
    tags = models.JSONField(default=list, blank=True)

    @property
    def record_locator(self) -> str:
        """
        Return the record locator, which is derived from ``key_id``.

        The primary key of a knox AuthToken is a digest string, not an integer id,
        so the TimestampedModel hashed_id-based record locator cannot be used.

        :returns: The locator, e.g. ``smarterauthtoken-d55cfbe5-89ec-4c11-90b9-3e9ec4bbbd85``.
        """
        return f"{self.__class__.__name__.lower()}-{self.key_id}"

    @property
    def tags_list(self) -> list[str]:
        """
        Return the tag names.

        ``tags`` is a JSONField list here, not a taggit manager.

        :returns: The tag names, or an empty list if ``tags`` is not a list.
        """
        tags = self.tags
        if not isinstance(tags, list):
            return []
        return [str(tag) for tag in tags]  # pylint: disable=not-an-iterable

    @classmethod
    def get_object_by_locator(cls, locator: str) -> Optional["SmarterAuthToken"]:
        """
        Return the SmarterAuthToken that a locator from :attr:`record_locator` identifies.

        :param locator: The record locator.
        :returns: The API key, or None if the locator is malformed or no key has its ``key_id``.
        """
        prefix = f"{cls.__name__.lower()}-"
        if not locator.startswith(prefix):
            return None
        try:
            return cls.objects.get(key_id=uuid.UUID(locator[len(prefix) :]))
        except (ValueError, cls.DoesNotExist):
            return None

    # TimestampedModel declares id as an int, the primary key of a normal row. This token's id is
    # deliberately its key_id string, so the override is intended.
    @property
    def id(self) -> str:  # type: ignore[override]  # pylint: disable=invalid-name  # pyright: ignore[reportIncompatibleVariableOverride]
        """
        Return the token's public identifier, its ``key_id``, as a string.

        A knox AuthToken has no integer id: its primary key is its digest. The api, the
        urls and the web console identify a token by its key_id instead.
        """
        return str(self.key_id)

    @property
    def hashed_id(self) -> str:  # type: ignore[override]
        """
        Return the token's public identifier.

        See :attr:`id`.
        """
        return self.id

    def clone(
        self,
        new_name: Optional[str] = None,
        new_version: Optional[str] = None,
        user_profile: Optional[UserProfile] = None,
    ) -> "SmarterAuthToken":
        """
        Create a new API key with this key's metadata.

        A clone is a new key: the manager creates its own token, digest and key_id, which
        MetaDataWithOwnershipModel.clone() would otherwise copy from this key.

        :param new_name: The name of the new key. Defaults to this key's name, suffixed with "_clone".
        :param new_version: The version of the new key. Defaults to this key's version.
        :param user_profile: The owner of the new key. Defaults to this key's owner.
        :returns: The new key.
        """
        user_profile = user_profile or self.user_profile
        clone, _ = SmarterAuthToken.objects.create(  # type: ignore[misc]
            user=user_profile.user,
            user_profile=user_profile,
            name=new_name or f"{self.name}_clone",
            description=self.description,
            version=new_version or self.version,
            annotations=self.annotations,
            tags=self.tags,
            is_active=self.is_active,
        )
        return clone

    def validate_token(self, token: str) -> bool:
        """
        Return whether a token is this API key's token, which is stored only as its digest.

        :param token: The plain token.
        :returns: True if the token's key and hash match this key's ``token_key`` and ``digest``.
        """
        if not token or token[: CONSTANTS.TOKEN_KEY_LENGTH] != self.token_key:
            return False
        return hmac.compare_digest(crypto.hash_token(token), self.digest)

    @property
    def identifier(self) -> str:
        """Return the token's digest, masked for logging."""
        return self.mask_string(self.digest)

    @property
    def manifest_url(self) -> Optional[str]:
        """
        Return the URL of the token's manifest detail page, which identifies the token by its key_id.

        **Example:**

        .. code-block:: python

            self.manifest_url  # '/authtoken/d55cfbe5-89ec-4c11-90b9-3e9ec4bbbd85/'
        """
        # pylint: disable=C0415
        from smarter.lib.drf.urls import AuthTokenReverseNames

        return reverse(
            f"{AuthTokenReverseNames.namespace}:{AuthTokenReverseNames.detailview}",
            kwargs={"authtoken_id": self.key_id},
        )

    def save(self, *args, **kwargs):
        """
        Save the API key, setting ``created`` if unset and converting ``name`` to snake_case.

        :param args: Passed to Django's ``save()``.
        :param kwargs: Passed to Django's ``save()``.
        :raises SmarterBusinessRuleViolation: If the key's user is not staff.
        """
        if not self.user.is_staff:
            raise SmarterBusinessRuleViolation("API Keys can only be created for staff users.")
        if self.created is None:
            self.created = timezone.now()
        if isinstance(self.name, str) and self.name and not SmarterValidator.is_valid_snake_case(self.name):
            snake_case_name = to_snake_case(self.name)
            logger.warning(
                "%s.%s.save(): name %s was not in snake_case. Converted to snake_case: %s",
                logger_prefix,
                self.__class__.__name__,
                self.name,
                snake_case_name,
            )
            self.name = snake_case_name
        super().save(*args, **kwargs)

    def activate(self):
        """Activate the API key, and save it."""
        self.is_active = True
        self.save()

    def deactivate(self):
        """Deactivate the API key, and save it."""
        self.is_active = False
        self.save()

    def toggle_active(self):
        """Toggle the API key's active status, and save it."""
        self.is_active = not self.is_active
        self.save()

    def last_used_is_stale(self, now: datetime) -> bool:
        """
        Return whether ``last_used_at`` is older than :data:`LAST_USED_RESOLUTION`.

        :param now: The current, timezone-aware time.
        :returns: True if the key was never used, or was last used longer ago than the resolution.
        """
        if self.last_used_at is None:
            return True
        age = now - self.last_used_at
        is_stale = age > LAST_USED_RESOLUTION
        return is_stale

    def accessed(self) -> None:
        """Update the last used time, and save, if it is older than :data:`LAST_USED_RESOLUTION`."""
        now = timezone.now()
        if self.last_used_is_stale(now):
            self.last_used_at = now
            self.save()

    @classmethod
    def get_cached_objects(
        cls,
        invalidate: Optional[bool] = False,
        user_profile: Optional[UserProfile] = None,
        taggit: bool = True,
        *,
        user: Optional[User] = None,
        name: Optional[str] = None,
        **kwargs,
    ) -> models.QuerySet["SmarterAuthToken"]:
        """
        Return the API keys of a user profile's user, optionally only those with a name, from the cache.

        The results are cached by :func:`cached_auth_tokens`, and invalidated whenever an API key
        is saved or deleted (see :mod:`smarter.lib.drf.receivers`).

        :param invalidate: If True, drop the cached result for this user profile and name first.
        :param user_profile: The user profile whose user's API keys are returned.
        :param taggit: Accepted for the base class's signature, and ignored.
        :param user: The user whose API keys are returned, used if ``user_profile`` is not given.
        :param name: If given, only the API keys with this name are returned.
        :param kwargs: Accepted for compatibility with the base class, and ignored.
        :returns: A queryset of the matching API keys, or every API key if neither
            ``user_profile`` nor ``user`` is given.
        """
        if user_profile is None and user is not None:
            user_profile = UserProfile.get_cached_object(user=user)

        if user_profile is None:
            return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]

        if invalidate:
            cached_auth_tokens.invalidate(user_profile.id, name)

        auth_tokens = cached_auth_tokens(user_profile.id, name)
        return auth_tokens

    def __str__(self) -> str:
        """Return the key's name, user and masked digest."""
        return str(self.name) + " (" + str(self.user) + ") " + str(self.identifier)


@cache_results(SmarterAuthToken.cache_expiration)
def cached_auth_tokens(user_profile_id: int, name: Optional[str]) -> models.QuerySet[SmarterAuthToken]:
    """
    Return the API keys of a user profile's user, optionally only those with a name.

    An API key belongs to a user, so every profile of the user sees the same keys.
    :func:`invalidate_cached_auth_tokens` drops the results of each of them.

    :param user_profile_id: The id of the user profile, part of the cache key.
    :param name: The name of the API keys, or None for all of them, part of the cache key.
    :returns: A queryset of the matching API keys.
    """
    user_ids = UserProfile.objects.filter(pk=user_profile_id).values_list("user_id", flat=True)
    queryset = SmarterAuthToken.objects.select_related(
        "user_profile", "user_profile__account", "user_profile__user"
    ).filter(user_id__in=user_ids)
    if name is not None:
        queryset = queryset.filter(name=name)
    return queryset


def invalidate_cached_auth_tokens(user_id: int, names: Iterable[Optional[str]]) -> None:
    """
    Drop the cached API keys of every profile of a user, for all names and for each of ``names``.

    :param user_id: The id of the user whose API keys changed.
    :param names: The names to drop, e.g. a key's new and old name. None and blank names are skipped.
    """
    user_profile_ids = UserProfile.objects.filter(user_id=user_id).values_list("pk", flat=True)
    for user_profile_id in user_profile_ids:
        cached_auth_tokens.invalidate(user_profile_id, None)
        for name in names:
            if name:
                cached_auth_tokens.invalidate(user_profile_id, name)
