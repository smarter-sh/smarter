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

from smarter.apps.account.models import User
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.lib.django.model_helpers import TimestampedModel


logger = getLogger(__name__)


###############################################################################
# API Key Management
###############################################################################
class SmarterAuthTokenManager(AuthTokenManager):
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
            "Creating API Key for user %s with token %s and expiry %s",
            user,
            token_key,
            expiry,
        )
        auth_token.save()
        return auth_token, token


class SmarterAuthToken(AuthToken, TimestampedModel):
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
    - ``TimestampedModel``: Provides created/modified timestamps.

    """

    objects = SmarterAuthTokenManager()

    # pylint: disable=C0115
    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    key_id = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=255, blank=True, null=True)
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

    def __str__(self):
        return str(self.name) + " (" + str(self.user) + ") " + str(self.identifier)
