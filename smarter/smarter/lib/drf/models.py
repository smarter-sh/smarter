"""DRF knox authtoken model and manager."""

import uuid
from datetime import datetime, timedelta
from logging import getLogger
from typing import Optional

from django.db import models
from django.utils import timezone
from knox import crypto
from knox.models import AuthToken, AuthTokenManager
from knox.settings import CONSTANTS

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    User,
    UserProfile,
)
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results

logger = getLogger(__name__)


###############################################################################
# API Key Management
###############################################################################
class SmarterAuthTokenManager(AuthTokenManager, models.Manager):
    """API Key manager."""

    def create(
        self,
        user: User,
        expiry=None,
        prefix=None,
        name: Optional[str] = None,
        description: Optional[str] = None,
        is_active: bool = True,
        **kwargs,
    ) -> tuple["SmarterAuthToken", str]:
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
        logger.info(
            "%s Creating API Key for user %s with token %s and expiry %s",
            formatted_text("lib.drf.models.SmarterAuthTokenManager.create()"),
            user,
            token_key,
            expiry,
        )
        auth_token.save()
        return auth_token, token


class SmarterAuthToken(AuthToken, MetaDataWithOwnershipModel):
    """
    Represents a Smarter API Key used for authenticating and authorizing access to the Smarter platform.

    This model extends Knox's `AuthToken` and includes additional metadata and management features
    for API keys, such as naming, description, activation status, and usage tracking.

    **Parameters:**
        key_id (UUIDField): Unique identifier for the API key.
        name (str): Human-readable name for the API key.
        description (str, optional): Optional description of the API key's purpose.
        last_used_at (datetime, optional): Timestamp of the last usage of the API key.
        is_active (bool): Indicates whether the API key is currently active.

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
          will raise a `SmarterBusinessRuleViolation`.
        - The `identifier` property returns a masked version of the key digest for display purposes.

    .. warning::

        - Ensure that API keys are managed securely. Deactivated keys cannot be used for authentication.
        - The `has_permissions` method checks if a user is staff or superuser before allowing management actions.

    Related Models
    --------------

    - ``User``: The owner of the API key.
    - ``MetaDataModel``: Provides created/modified timestamps and SAM metadata.

    """

    objects = SmarterAuthTokenManager()

    # pylint: disable=C0115
    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    key_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
    tags = models.JSONField(default=list, blank=True)
    last_used_at = models.DateTimeField(blank=True, null=True)
    is_active = models.BooleanField(default=True)

    @property
    def identifier(self):
        return "******" + str(self.digest)[-4:]

    def save(self, *args, **kwargs):
        if not self.user.is_staff:
            raise SmarterBusinessRuleViolation("API Keys can only be created for staff users.")
        if self.created is None:
            self.created = timezone.now()
        super().save(*args, **kwargs)

    def has_permissions(self, user) -> bool:
        """Determine if the authenticated user has permissions to manage this key."""
        if not hasattr(user, "is_authenticated") or not user.is_authenticated:
            return False
        if not hasattr(user, "is_staff") or not hasattr(user, "is_superuser"):
            return False
        return user.is_staff or user.is_superuser

    def activate(self):
        """Activate the API key."""
        self.is_active = True
        self.save()

    def deactivate(self):
        """Deactivate the API key."""
        self.is_active = False
        self.save()

    def toggle_active(self):
        """Toggle the active status of the API key."""
        self.is_active = not self.is_active
        self.save()

    def accessed(self):
        """Update the last used time."""
        if self.last_used_at is None or (datetime.now() - self.last_used_at) > timedelta(minutes=5):
            self.last_used_at = datetime.now()
            self.save()

    @classmethod
    def get_cached_objects(
        cls,
        invalidate: Optional[bool] = False,
        user_profile: Optional[UserProfile] = None,
        user: Optional[User] = None,
        name: Optional[str] = None,
    ) -> models.QuerySet["SmarterAuthToken"]:
        """
        Retrieve API keys with caching based on user profile and optional name
        filter using caching.

        :param invalidate: If True, invalidate the cache for this query.
        :type invalidate: bool, optional
        :param user_profile: The user profile for which to retrieve API keys.
        :type user_profile: UserProfile, optional
        :param user: The user for which to retrieve API keys (used if user_profile is not provided).
        :type user: User, optional
        :param name: Optional name filter to retrieve API keys with a specific name.
        :type name: str, optional

        :returns: A queryset of SmarterAuthToken objects matching the criteria.
        :rtype: QuerySet[SmarterAuthToken]
        """
        logger_prefix = formatted_text(f"{__name__}.{cls.__name__}.get_cached_objects()")
        logger.debug(
            "%s called with user_profile=%s, user=%s, name=%s, invalidate=%s",
            logger_prefix,
            user_profile,
            user,
            name,
            invalidate,
        )

        # pylint: disable=W0613
        @cache_results(cls.cache_expiration)
        def _get_cached_objects_for_user_profile(user_profile_id: int) -> models.QuerySet["SmarterAuthToken"]:
            queryset = (
                cls.objects.prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
                .filter(user=user_profile.cached_user)
            )
            return queryset

        # pylint: disable=W0613
        @cache_results(cls.cache_expiration)
        def _get_cached_objects_for_user_profile_and_name(
            user_profile_id: int, name: str
        ) -> models.QuerySet["SmarterAuthToken"]:
            """
            Retrieve API keys for a specific user profile and name with caching.

            :param user_profile_id: The ID of the user profile for which to retrieve API keys.
            :type user_profile_id: int
            :param name: The name of the API key to retrieve.
            :type name: str

            :returns: A queryset of SmarterAuthToken objects matching the criteria.
            :rtype: QuerySet[SmarterAuthToken]
            """
            queryset = (
                cls.objects.prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
                .filter(user=user_profile.cached_user, name=name)
            )
            return queryset

        if invalidate:
            # Invalidate the cache for both functions
            _get_cached_objects_for_user_profile.invalidate_cache(
                user_profile_id=user_profile.id if user_profile else None
            )
            _get_cached_objects_for_user_profile_and_name.invalidate_cache(
                user_profile_id=user_profile.id if user_profile else None, name=name
            )

        if not user_profile and user:
            user_profile = UserProfile.get_cached_object(user=user)

        if user_profile and name:
            return _get_cached_objects_for_user_profile_and_name(user_profile.id, name)
        elif user_profile:
            return _get_cached_objects_for_user_profile(user_profile.id)
        else:
            return super().get_cached_objects(user_profile=user_profile, invalidate=invalidate)  # type: ignore

    def __str__(self):
        return str(self.name) + " (" + str(self.user) + ") " + str(self.identifier)
