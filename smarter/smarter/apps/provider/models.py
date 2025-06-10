# pylint: disable=W0613,C0115
"""All models for the Provider app."""

import logging

from django.db import models

from smarter.apps.account.models import Account
from smarter.common.exceptions import SmarterValueError
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.user import User

from .signals import (
    provider_activated,
    provider_deactivated,
    provider_deprecated,
    provider_flagged,
    provider_suspended,
    provider_undeprecated,
    provider_unflagged,
    provider_unsuspended,
    verification_requested,
)


logger = logging.getLogger(__name__)


class ProviderStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    VERIFYING = "verifying", "Verifying"
    FAILED = "failed", "Verification Failed"
    VERIFIED = "verified", "Verified"
    SUSPENDED = "suspended", "Suspended"
    DEPRECATED = "deprecated", "Deprecated"


class Provider(TimestampedModel):
    """Chat model."""

    class Meta:
        verbose_name = "Provider"
        verbose_name_plural = "Providers"

    account = models.ForeignKey(Account, on_delete=models.CASCADE, blank=False, null=False)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    status = models.CharField(
        max_length=32,
        choices=ProviderStatus.choices,
        default=ProviderStatus.UNVERIFIED,
        blank=False,
        null=False,
    )
    is_active = models.BooleanField(default=False, blank=False, null=False)
    is_verified = models.BooleanField(default=False, blank=False, null=False)
    is_featured = models.BooleanField(default=False, blank=False, null=False)
    is_deprecated = models.BooleanField(default=False, blank=False, null=False)
    is_flagged = models.BooleanField(default=False, blank=False, null=False)
    is_suspended = models.BooleanField(default=False, blank=False, null=False)
    api_url = models.URLField(max_length=255, blank=True, null=True, help_text="The base URL for the provider's API.")
    logo = models.ImageField(
        upload_to="provider_logos/",
        blank=True,
        null=True,
        help_text="The logo of the provider.",
    )
    website = models.URLField(max_length=255, blank=True, null=True, help_text="The website URL of the provider.")
    contact_email = models.EmailField(
        max_length=255, blank=True, null=True, help_text="The contact email of the provider."
    )
    support_email = models.EmailField(
        max_length=255, blank=True, null=True, help_text="The support email of the provider."
    )
    terms_of_service = models.URLField(
        max_length=255, blank=True, null=True, help_text="The terms of service URL of the provider."
    )
    privacy_policy = models.URLField(
        max_length=255, blank=True, null=True, help_text="The privacy policy URL of the provider."
    )
    tos_accepted = models.BooleanField(
        default=False, blank=False, null=False, help_text="Whether the terms of service have been accepted."
    )
    tos_accepted_at = models.DateTimeField(
        blank=True, null=True, help_text="The date and time when the terms of service were accepted."
    )
    tos_accepted_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="tos_accepted_by",
        help_text="The user who accepted the terms of service.",
    )

    @property
    def can_activate(self) -> bool:
        """Check if the provider can be activated."""
        return (
            self.status == ProviderStatus.VERIFIED
            and not self.is_deprecated
            and not self.is_suspended
            and not self.is_flagged
            and self.tos_accepted
            and self.tos_accepted_at is not None
            and self.tos_accepted_by is not None
        )

    def verify(self):
        """
        Request a batch of acceptance tests.
        Set the status but don't change the is_verified flag.
        This is used to indicate that the provider is being verified but has not yet been activated.
        """
        self.status = ProviderStatus.VERIFYING
        self.save()
        verification_requested.send(
            sender=self.__class__,
            instance=self,
        )

    def activate(self):
        """Activate the provider."""
        if not self.can_activate:
            if self.is_active:
                self.deactivate()
            if self.is_deprecated:
                raise SmarterValueError("Provider is deprecated and cannot be activated.")
            if self.is_suspended:
                raise SmarterValueError("Provider is suspended and cannot be activated.")
            if self.is_flagged:
                raise SmarterValueError("Provider is flagged and cannot be activated.")
            if not self.tos_accepted:
                raise SmarterValueError("Terms of service must be accepted before activation.")
            if self.tos_accepted_at is None:
                raise SmarterValueError("Terms of service acceptance date must be set before activation.")
            if self.tos_accepted_by is None:
                raise SmarterValueError("Terms of service acceptance user must be set before activation.")
            if self.status != ProviderStatus.VERIFIED:
                raise SmarterValueError("Provider must be verified before activation.")
        if not self.is_active:
            self.is_active = True
            self.save()
            provider_activated.send(
                sender=self.__class__,
                instance=self,
            )

    def deactivate(self):
        """Deactivate the provider."""
        self.is_active = False
        self.save()
        provider_deactivated.send(
            sender=self.__class__,
            instance=self,
        )

    def suspend(self):
        """Suspend the provider."""
        self.status = ProviderStatus.SUSPENDED
        self.is_suspended = True
        self.save()
        self.deactivate()
        provider_suspended.send(
            sender=self.__class__,
            instance=self,
        )

    def unsuspend(self):
        """Unsuspend the provider."""
        self.reset()
        provider_unsuspended.send(
            sender=self.__class__,
            instance=self,
        )

    def deprecate(self):
        """Deprecate the provider."""
        self.status = ProviderStatus.DEPRECATED
        self.is_deprecated = True
        self.save()
        self.deactivate()
        provider_deprecated.send(
            sender=self.__class__,
            instance=self,
        )

    def undeprecate(self):
        """Undeprecate the provider."""
        self.reset()
        provider_undeprecated.send(
            sender=self.__class__,
            instance=self,
        )

    def flag(self):
        """Flag the provider."""
        self.is_flagged = True
        self.save()
        self.deactivate()
        provider_flagged.send(
            sender=self.__class__,
            instance=self,
        )

    def unflag(self):
        """Unflag the provider."""
        self.is_flagged = False
        self.save()
        if self.can_activate:
            self.activate()
        else:
            self.reset()
        provider_unflagged.send(
            sender=self.__class__,
            instance=self,
        )

    def reset(self):
        """Reset the provider to its initial state."""
        self.status = ProviderStatus.UNVERIFIED
        self.is_active = False
        self.is_verified = False
        self.is_deprecated = False
        self.is_flagged = False
        self.is_suspended = False
        self.save()


class ProviderCompletionModels(TimestampedModel):
    """Provider completion models for a provider."""

    class Meta:
        verbose_name = "Provider Completion Model"
        verbose_name_plural = "Provider Completion Models"

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, blank=False, null=False)
    model_name = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True, null=True)
    is_default = models.BooleanField(default=False, blank=False, null=False)
    is_active = models.BooleanField(default=True, blank=False, null=False)
    is_deprecated = models.BooleanField(default=False, blank=False, null=False)
    is_flagged = models.BooleanField(default=False, blank=False, null=False)
    is_suspended = models.BooleanField(default=False, blank=False, null=False)

    supports_streaming = models.BooleanField(default=False, blank=False, null=False)
    supports_tools = models.BooleanField(default=False, blank=False, null=False)
    supports_text_input = models.BooleanField(default=True, blank=False, null=False)
    supports_image_input = models.BooleanField(default=False, blank=False, null=False)
    supports_audio_input = models.BooleanField(default=False, blank=False, null=False)
    supports_embedding = models.BooleanField(default=False, blank=False, null=False)
    supports_fine_tuning = models.BooleanField(default=False, blank=False, null=False)
    supports_search = models.BooleanField(default=False, blank=False, null=False)
    supports_code_interpreter = models.BooleanField(default=False, blank=False, null=False)
    supports_image_generation = models.BooleanField(default=False, blank=False, null=False)
    supports_audio_generation = models.BooleanField(default=False, blank=False, null=False)
    supports_text_generation = models.BooleanField(default=True, blank=False, null=False)
    supports_translation = models.BooleanField(default=False, blank=False, null=False)
    supports_summarization = models.BooleanField(default=False, blank=False, null=False)

    max_tokens = models.PositiveIntegerField(default=4096, blank=False, null=False)
    temperature = models.FloatField(default=0.7, blank=False, null=False)
    top_p = models.FloatField(default=1.0, blank=False, null=False)

    def __str__(self):
        """String representation of the model."""
        return f"{self.provider.name} - {self.model_name}"
