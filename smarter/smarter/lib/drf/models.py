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
    """Smarter API Key model."""

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
