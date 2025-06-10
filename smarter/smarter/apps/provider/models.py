# pylint: disable=W0613,C0115
"""All models for the Provider app."""

import logging
import os
import urllib.parse

import requests
from django.db import models

from smarter.apps.account.models import Account, Secret
from smarter.common.classes import SmarterHelperMixin
from smarter.common.exceptions import (
    SmarterBusinessRuleViolation,
    SmarterConfigurationError,
    SmarterValueError,
)
from smarter.lib.cache import cache_results
from smarter.lib.django.model_helpers import TimestampedModel
from smarter.lib.django.user import User

from .const import VERIFICATION_LIFETIME
from .enum import ProviderModelEnum
from .signals import (
    provider_activated,
    provider_deactivated,
    provider_deprecated,
    provider_flagged,
    provider_suspended,
    provider_undeprecated,
    provider_unflagged,
    provider_unsuspended,
    provider_verification_requested,
)


logger = logging.getLogger(__name__)
CACHE_TIMEOUT = 60 / 2  # 30 seconds


class ProviderStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    VERIFYING = "verifying", "Verifying"
    FAILED = "failed", "Verification Failed"
    VERIFIED = "verified", "Verified"
    SUSPENDED = "suspended", "Suspended"
    DEPRECATED = "deprecated", "Deprecated"


class ProviderModelVerificationTypes(models.TextChoices):
    STREAMING = "streaming", "Streaming"
    TOOLS = "tools", "Tools"
    TEXT_INPUT = "text_input", "Text Input"
    IMAGE_INPUT = "image_input", "Image Input"
    AUDIO_INPUT = "audio_input", "Audio Input"
    FINE_TUNING = "fine_tuning", "Fine Tuning"
    SEARCH = "search", "Search"
    CODE_INTERPRETER = "code_interpreter", "Code Interpreter"
    TEXT_TO_IMAGE = "text_to_image", "Text to Image"
    TEXT_TO_AUDIO = "text_to_audio", "Text to Audio"
    TEXT_TO_TEXT = "text_to_text", "Text to Text"
    TRANSLATION = "translation", "Translation"
    SUMMARIZATION = "summarization", "Summarization"


class Provider(TimestampedModel, SmarterHelperMixin):
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
    # good things
    is_active = models.BooleanField(default=False, blank=False, null=False)
    is_verified = models.BooleanField(default=False, blank=False, null=False)
    is_featured = models.BooleanField(default=False, blank=False, null=False)

    # bad things
    is_deprecated = models.BooleanField(default=False, blank=False, null=False)
    is_flagged = models.BooleanField(default=False, blank=False, null=False)
    is_suspended = models.BooleanField(default=False, blank=False, null=False)

    # connectivity
    api_url = models.URLField(max_length=255, blank=True, null=True, help_text="The base URL for the provider's API.")
    api_key = models.ForeignKey(
        Secret,
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="provider_api_key",
        help_text="The API key for the provider.",
    )
    connectivity_test_path = models.CharField(
        max_length=255,
        default="",
        blank=True,
        null=True,
        help_text="The URL to test connectivity with the provider's API.",
    )

    # Provider metadata
    logo = models.ImageField(
        upload_to="provider_logos/",
        blank=True,
        null=True,
        help_text="The logo of the provider.",
    )
    website = models.URLField(max_length=255, blank=True, null=True, help_text="The website URL of the provider.")
    ownership_requested = models.EmailField(
        max_length=255,
        blank=True,
        null=True,
        help_text="The email address of an alternative contact who has requested to take ownership of the provider.",
    )
    contact_email = models.EmailField(
        max_length=255, blank=True, null=True, help_text="The contact email of the provider."
    )
    contact_email_verified = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The date and time when the contact email was verified.",
    )
    support_email = models.EmailField(
        max_length=255, blank=True, null=True, help_text="The support email of the provider."
    )
    support_email_verified = models.DateTimeField(
        blank=True,
        null=True,
        help_text="The date and time when the support email was verified.",
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
    def authorization_header(self) -> dict:
        """Return the authorization header for the provider."""
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key.secret}"}
        return {}

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

    def test_connectivity(self) -> bool:
        """
        Test connectivity to the provider's API.
        This method should be overridden by subclasses to implement specific connectivity tests.
        """
        if not self.api_url:
            raise SmarterValueError("api_url is not set for this provider.")
        url = urllib.parse.urljoin(self.api_url, self.connectivity_test_path)
        try:
            if self.api_key is not None:
                logger.info(
                    "%s verifying API connectivity and key for %s with URL: %s",
                    self.formatted_class_name,
                    self.name,
                    url,
                )
                response = requests.get(url, headers=self.authorization_header, timeout=10)
            else:
                logger.info(
                    "%s verifying API connectivity for %s with URL: %s", self.formatted_class_name, self.name, url
                )
                response = requests.get(url, timeout=10)
            if response.status_code == 200:
                return True
            else:
                logger.error(
                    "%s API URL and key verification for %s failed with status code: %s",
                    self.formatted_class_name,
                    self.name,
                    response.status_code,
                )
                return False
        except requests.RequestException as exc:
            logger.error(
                "%s Got an unexpected error testing API URL and key verification for %s failed: %s",
                self.formatted_class_name,
                self.name,
                exc,
            )
            return False

    def verify(self):
        """
        Request a batch of acceptance tests.
        Set the status but don't change the is_verified flag.
        This is used to indicate that the provider is being verified but has not yet been activated.
        """
        self.status = ProviderStatus.VERIFYING
        self.save()
        provider_verification_requested.send(
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

    def __str__(self):
        """String representation of the provider."""
        return f"{self.name} ({self.account.account_number}) - {self.status}"


class ProviderModel(TimestampedModel):
    """Provider completion models for a provider."""

    class Meta:
        verbose_name = "Provider Model"
        verbose_name_plural = "Provider Models"
        unique_together = (("provider", "name"),)

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, blank=False, null=False)
    name = models.CharField(max_length=255, blank=False, null=False)
    description = models.TextField(blank=True, null=True)

    # good things
    is_default = models.BooleanField(default=False, blank=False, null=False)
    is_active = models.BooleanField(default=True, blank=False, null=False)

    # bad things
    is_deprecated = models.BooleanField(default=False, blank=False, null=False)
    is_flagged = models.BooleanField(default=False, blank=False, null=False)
    is_suspended = models.BooleanField(default=False, blank=False, null=False)

    # model configuration
    max_tokens = models.PositiveIntegerField(default=4096, blank=False, null=False)
    temperature = models.FloatField(default=0.7, blank=False, null=False)
    top_p = models.FloatField(default=1.0, blank=False, null=False)

    # verifiable features
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

    def __str__(self):
        """String representation of the model."""
        return f"{self.provider.name} - {self.name}"


class ProviderModelVerification(TimestampedModel):
    """Provider completion model verifications for a provider."""

    class Meta:
        verbose_name = "Provider Model Verification"
        verbose_name_plural = "Provider Model Verifications"
        unique_together = (("provider_model", "verification_type"),)

    provider_model = models.ForeignKey(ProviderModel, on_delete=models.CASCADE, blank=False, null=False)
    verification_type = models.CharField(
        max_length=32,
        choices=ProviderModelVerificationTypes.choices,
        default=ProviderModelVerificationTypes.TEXT_INPUT,
        blank=False,
        null=False,
    )
    is_successful = models.BooleanField(default=False, blank=False, null=False)
    error_message = models.TextField(blank=True, null=True)

    @property
    def is_valid(self) -> bool:
        """Check if the verification is valid."""
        return self.is_successful and self.elapsed_updated < VERIFICATION_LIFETIME

    def __str__(self):
        """String representation of the verification."""
        return f"{self.provider_model.name} - {self.verification_type}: {'Success' if self.is_successful else 'Failed'}"


@cache_results(timeout=CACHE_TIMEOUT)
def get_model_for_provider(account_number: str, provider_name: str, model_name: str = None) -> dict:
    """
    Get the model for a provider by name and account number. This is the
    primary way to retrieve a model for a provider. Raises a Smarter error if
    anything goes wrong.
    """

    # get the account that owns the provider. Long term this is envisioned to be
    # OpenAI, GoogleAI et al. But for now, assume that Smarter owns all of the
    # Providers.
    try:
        account = Account.objects.get(account_number=account_number)
    except Account.DoesNotExist as e:
        raise SmarterValueError(f"Account with number {account_number} does not exist.") from e

    # check if the account is active.
    if not account.is_active:
        raise SmarterBusinessRuleViolation(f"Account {account_number} is not active.")

    # get the provider master record
    try:
        provider = Provider.objects.get(account=account, name=provider_name)
    except Provider.DoesNotExist as e:
        raise SmarterValueError(f"Provider {provider_name} does not exist for account {account.account_number}.") from e

    # the Provider might be inactive for a variety of reasons: suspended, flagged, deprecated, or something else.
    # We don't care why we just want to know if it is active or not.
    if not provider.is_active:
        raise SmarterBusinessRuleViolation(f"Provider {provider_name} is not active.")

    # get the model for the provider
    if model_name is not None:
        try:
            model = ProviderModel.objects.get(provider=provider, name=model_name)
        except ProviderModel.DoesNotExist as e:
            raise SmarterValueError(f"Model {model_name} for provider {provider_name} does not exist.") from e
    else:
        try:
            model = ProviderModel.objects.get(provider=provider, is_default=True)
        except ProviderModel.DoesNotExist as e:
            raise SmarterValueError(f"No default model found for provider {provider_name}.") from e

    # The model is periodically re-verified and is therefore subject to being inactived if any of
    # it's verification tests fail.
    # Again, we don't care why it is inactive, we just want to know if it is active or not.
    if not model.is_active:
        raise SmarterBusinessRuleViolation(f"Model {model_name} for provider {provider_name} is not active.")

    # get the production api key
    api_key_name = f"{provider.name.upper()}_API_KEY"
    api_key = os.environ.get(api_key_name)
    if not api_key:
        raise SmarterConfigurationError(
            f"Production API key for provider {provider_name} is not set in environment variables."
        )

    return {
        ProviderModelEnum.API_KEY.value: api_key,
        ProviderModelEnum.PROVIDER_NAME.value: provider.name,
        ProviderModelEnum.PROVIDER_ID.value: provider.id,
        ProviderModelEnum.BASE_URL.value: provider.api_url,
        ProviderModelEnum.DEFAULT_MODEL.value: model.name,
        ProviderModelEnum.MAX_TOKENS.value: model.max_tokens,
        ProviderModelEnum.TEMPERATURE.value: model.temperature,
        ProviderModelEnum.TOP_P.value: model.top_p,
        ProviderModelEnum.VALID_CHAT_COMPLETION_MODELS.value: [model.name],
    }
