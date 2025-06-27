# pylint: disable=W0613,C0115
"""All models for the Provider app."""

import datetime
import logging
import os
import urllib.parse
from typing import Optional, TypedDict

import requests
from django.db import models

from smarter.apps.account.models import Account, Secret
from smarter.apps.account.models import UserClass as User
from smarter.common.classes import SmarterHelperMixin
from smarter.common.exceptions import (
    SmarterBusinessRuleViolation,
    SmarterConfigurationError,
    SmarterValueError,
)
from smarter.lib.cache import cache_results
from smarter.lib.django.model_helpers import TimestampedModel

from .const import VERIFICATION_LEAD_TIME, VERIFICATION_LIFETIME
from .manifest.enum import ProviderModelEnum
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
CACHE_TIMEOUT = int(60 / 2)  # 30 seconds


class ProviderModelTypedDict(TypedDict):
    """TypedDict for provider model information."""

    api_key: str
    provider_name: str
    provider_id: int
    base_url: str
    model: str
    max_tokens: int
    temperature: float
    top_p: float
    supports_streaming: bool
    supports_tools: bool
    supports_text_input: bool
    supports_image_input: bool
    supports_audio_input: bool
    supports_embedding: bool
    supports_fine_tuning: bool
    supports_search: bool
    supports_code_interpreter: bool
    supports_image_generation: bool
    supports_audio_generation: bool
    supports_text_generation: bool
    supports_translation: bool
    supports_summarization: bool


class ProviderStatus(models.TextChoices):
    UNVERIFIED = "unverified", "Unverified"
    VERIFYING = "verifying", "Verifying"
    FAILED = "failed", "Verification Failed"
    VERIFIED = "verified", "Verified"
    SUSPENDED = "suspended", "Suspended"
    DEPRECATED = "deprecated", "Deprecated"


class ProviderVerificationTypes(models.TextChoices):
    API_CONNECTIVITY = "api_connectivity", "Api Connectivity"
    LOGO = "logo", "Logo"
    CONTACT_EMAIL = "contact_email", "Contact Email"
    SUPPORT_EMAIL = "support_email", "Support Email"
    WEBSITE_URL = "website_url", "Website URL"
    TOS_URL = "tos_url", "Terms of Service URL"
    PRIVACY_POLICY_URL = "privacy_policy_url", "Privacy Policy URL"
    TOS_ACCEPTANCE = "tos_acceptance", "Terms of Service Acceptance"
    PRODUCTION_API_KEY = "production_api_key", "Production API Key"


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

    account = models.ForeignKey(
        Account, on_delete=models.CASCADE, blank=False, null=False, help_text="The account that owns the provider."
    )
    owner = models.ForeignKey(
        User, on_delete=models.CASCADE, blank=False, null=False, help_text="The users that owns the provider."
    )
    name = models.CharField(max_length=255, blank=False, null=False, unique=True, help_text="The name of the provider.")
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
    base_url = models.URLField(max_length=255, blank=True, null=True, help_text="The base URL for the provider's API.")
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
    website_url = models.URLField(
        max_length=255, blank=True, null=True, help_text="The website_url URL of the provider."
    )
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
    docs_url = models.URLField(
        max_length=255, blank=True, null=True, help_text="The documentation URL of the provider."
    )
    terms_of_service_url = models.URLField(
        max_length=255, blank=True, null=True, help_text="The terms of service URL of the provider."
    )
    privacy_policy_url = models.URLField(
        max_length=255, blank=True, null=True, help_text="The privacy policy URL of the provider."
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
    def tos_accepted(self) -> bool:
        """Check if the terms of service have been accepted."""
        return self.tos_accepted_at is not None and self.tos_accepted_by is not None

    def production_api_key(self, mask: bool = True) -> str:
        """Return the production API key for the provider."""
        api_key_name = f"{self.name.upper()}_API_KEY"
        api_key = os.environ.get(api_key_name)
        if api_key is None:
            raise SmarterConfigurationError(
                f"Production API key for provider {self.name} was accessed but is not set in environment variables."
            )
        return api_key if not mask else "********"

    @property
    def authorization_header(self) -> dict:
        """Return the authorization header for the provider."""
        if self.production_api_key(mask=False) is not None:
            return {"Authorization": f"Bearer {self.production_api_key(mask=False)}"}
        if self.api_key:
            return {"Authorization": f"Bearer {self.api_key.get_secret()}"}
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
        if not self.base_url:
            raise SmarterValueError("base_url is not set for this provider.")
        url = urllib.parse.urljoin(self.base_url, self.connectivity_test_path)
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
    is_active = models.BooleanField(default=False, blank=False, null=False)

    # bad things
    is_deprecated = models.BooleanField(default=False, blank=False, null=False)
    is_flagged = models.BooleanField(default=False, blank=False, null=False)
    is_suspended = models.BooleanField(default=False, blank=False, null=False)

    # model configuration
    max_tokens = models.PositiveIntegerField(default=4096, blank=False, null=False)
    temperature = models.FloatField(default=0.7, blank=False, null=False)
    top_p = models.FloatField(default=1.0, blank=False, null=False)

    # verifiable features - defaults to True
    supports_text_input = models.BooleanField(default=True, blank=False, null=False)
    supports_text_generation = models.BooleanField(default=True, blank=False, null=False)
    supports_translation = models.BooleanField(default=True, blank=False, null=False)
    supports_summarization = models.BooleanField(default=True, blank=False, null=False)

    # verifiable features - defaults to False
    supports_streaming = models.BooleanField(default=False, blank=False, null=False)
    supports_tools = models.BooleanField(default=False, blank=False, null=False)
    supports_image_input = models.BooleanField(default=False, blank=False, null=False)
    supports_audio_input = models.BooleanField(default=False, blank=False, null=False)
    supports_embedding = models.BooleanField(default=False, blank=False, null=False)
    supports_fine_tuning = models.BooleanField(default=False, blank=False, null=False)
    supports_search = models.BooleanField(default=False, blank=False, null=False)
    supports_code_interpreter = models.BooleanField(default=False, blank=False, null=False)
    supports_image_generation = models.BooleanField(default=False, blank=False, null=False)
    supports_audio_generation = models.BooleanField(default=False, blank=False, null=False)

    def __str__(self):
        """String representation of the model."""
        return f"{self.provider.name} - {self.name}"


# ------------------------------------------------------------------------------
# Verification history for providers and provider models
# ------------------------------------------------------------------------------
class ProviderVerification(TimestampedModel):
    """Provider completion model verifications for a provider."""

    class Meta:
        verbose_name = "Provider Verification"
        verbose_name_plural = "Provider Verifications"
        unique_together = (("provider", "verification_type"),)

    provider = models.ForeignKey(Provider, on_delete=models.CASCADE, blank=False, null=False)
    verification_type = models.CharField(
        max_length=32,
        choices=ProviderVerificationTypes.choices,
        default=ProviderVerificationTypes.API_CONNECTIVITY,
        blank=False,
        null=False,
    )
    is_successful = models.BooleanField(default=False, blank=False, null=False)
    error_message = models.TextField(blank=True, null=True)

    @property
    def is_valid(self) -> bool:
        """Check if the verification is valid."""
        return self.is_successful and self.elapsed_updated < VERIFICATION_LIFETIME

    @property
    def next_verification(self) -> datetime.datetime:
        """Get the next verification time."""
        return self.updated_at + VERIFICATION_LIFETIME - VERIFICATION_LEAD_TIME

    def __str__(self):
        """String representation of the verification."""
        return f"{self.provider.name} - {self.verification_type}: {'Success' if self.is_successful else 'Failed'}"


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

    @property
    def next_verification(self) -> datetime.datetime:
        """Get the next verification time."""
        return self.updated_at + VERIFICATION_LIFETIME - VERIFICATION_LEAD_TIME

    def __str__(self):
        """String representation of the verification."""
        return f"{self.provider_model.name} - {self.verification_type}: {'Success' if self.is_successful else 'Failed'}"


@cache_results(timeout=CACHE_TIMEOUT)
def get_provider(provider_name: str) -> Provider:
    """
    Get the provider by name and account number. This is the primary way to
    retrieve a provider. Raises a Smarter error if anything goes wrong.
    """

    try:
        provider = Provider.objects.get(name=provider_name)
    except Provider.DoesNotExist as e:
        raise SmarterValueError(f"Provider {provider_name} does not exist.") from e

    if not provider.account.is_active:
        raise SmarterBusinessRuleViolation(f"Provider account {provider.account.account_number} is not active.")

    # the Provider might be inactive for a variety of reasons: suspended, flagged, deprecated, or something else.
    # We don't care why we just want to know if it is active or not.
    if not provider.is_active:
        raise SmarterBusinessRuleViolation(f"Provider {provider_name} is not active.")

    return provider


@cache_results(timeout=CACHE_TIMEOUT)
def get_providers() -> list[Provider]:
    """
    Get all active providers. This is the primary way to retrieve all providers.
    Raises a Smarter error if anything goes wrong.
    """
    try:
        providers = Provider.objects.filter(is_active=True)
    except Provider.DoesNotExist as e:
        raise SmarterValueError("No active providers found.") from e

    return list(providers)


@cache_results(timeout=CACHE_TIMEOUT)
def get_model_for_provider(provider_name: str, model_name: Optional[str] = None) -> ProviderModelTypedDict:
    """
    Get the model for a provider by name and account number. This is the
    primary way to retrieve a model for a provider. Raises a Smarter error if
    anything goes wrong.
    """
    provider = get_provider(provider_name=provider_name)

    # the Provider might be inactive for a variety of reasons: suspended, flagged, deprecated, or something else.
    # We don't care why we just want to know if it is active or not.
    if not provider.is_active:
        raise SmarterBusinessRuleViolation(f"Provider {provider_name} is not active.")

    # 3.) get the model for the provider
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

    return {
        ProviderModelEnum.API_KEY.value: provider.production_api_key(mask=False),
        ProviderModelEnum.PROVIDER_NAME.value: provider.name,
        ProviderModelEnum.PROVIDER_ID.value: provider.id,  # type: ignore[union-attr]
        ProviderModelEnum.BASE_URL.value: provider.base_url,
        ProviderModelEnum.MODEL.value: model.name,
        ProviderModelEnum.MAX_TOKENS.value: model.max_tokens,
        ProviderModelEnum.TEMPERATURE.value: model.temperature,
        ProviderModelEnum.TOP_P.value: model.top_p,
        ProviderModelEnum.SUPPORTS_STREAMING.value: model.supports_streaming,
        ProviderModelEnum.SUPPORTS_TOOLS.value: model.supports_tools,
        ProviderModelEnum.SUPPORTS_TEXT_INPUT.value: model.supports_text_input,
        ProviderModelEnum.SUPPORTS_IMAGE_INPUT.value: model.supports_image_input,
        ProviderModelEnum.SUPPORTS_AUDIO_INPUT.value: model.supports_audio_input,
        ProviderModelEnum.SUPPORTS_EMBEDDING.value: model.supports_embedding,
        ProviderModelEnum.SUPPORTS_FINE_TUNING.value: model.supports_fine_tuning,
        ProviderModelEnum.SUPPORTS_SEARCH.value: model.supports_search,
        ProviderModelEnum.SUPPORTS_CODE_INTERPRETER.value: model.supports_code_interpreter,
        ProviderModelEnum.SUPPORTS_IMAGE_GENERATION.value: model.supports_image_generation,
        ProviderModelEnum.SUPPORTS_AUDIO_GENERATION.value: model.supports_audio_generation,
        ProviderModelEnum.SUPPORTS_TEXT_GENERATION.value: model.supports_text_generation,
        ProviderModelEnum.SUPPORTS_TRANSLATION.value: model.supports_translation,
        ProviderModelEnum.SUPPORTS_SUMMARIZATION.value: model.supports_summarization,
    }


@cache_results(timeout=CACHE_TIMEOUT)
def get_models_for_provider(provider_name: str) -> list[ProviderModelTypedDict]:
    """
    Get all models for a provider by name and account number. This is the
    primary way to retrieve all models for a provider. Raises a Smarter error if
    anything goes wrong.
    """
    provider = get_provider(provider_name=provider_name)
    provider_models = ProviderModel.objects.filter(provider=provider, is_active=True)

    return [
        get_model_for_provider(provider_name=provider_name, model_name=provider_model.name)
        for provider_model in provider_models
    ]
