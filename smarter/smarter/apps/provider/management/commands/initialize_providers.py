"""This module is used to generate seed records for the prompt history models."""

import base64
import logging
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urljoin

import requests
from django.core.files.base import ContentFile
from django.utils import timezone
from pydantic import SecretStr

from smarter.apps.account.models import UserProfile
from smarter.apps.account.utils import smarter_cached_objects
from smarter.apps.provider.const import (
    GOOGLE_MAPS_API_KEY_SECRET_NAME,
    GOOGLE_SERVICE_ACCOUNT_SECRET_NAME,
)
from smarter.apps.provider.models import Provider, ProviderModel, ProviderStatus
from smarter.apps.provider.utils import get_google_service_account_bearer_token
from smarter.apps.secret.models import Secret
from smarter.common.conf.const import get_env
from smarter.common.const import SMARTER_CONTACT_EMAIL, SMARTER_CUSTOMER_SUPPORT_EMAIL
from smarter.lib import json
from smarter.lib.django.management.base import SmarterCommand

logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent


class Command(SmarterCommand):
    """
    Django manage.py initialize_providers.py command.

    This command is used to create/update the principal
    Providers that are preloaded on all platforms.

    This runs during deployment.
    """

    user_profile: UserProfile

    def initialize_google_service_account(self):
        """Initialize Google service account credentials."""
        try:
            svc_acct_b64 = get_env("GOOGLE_SERVICE_ACCOUNT_B64", "", is_secret=True, is_required=True)
            secret_string = SecretStr(json.loads(base64.b64decode(svc_acct_b64).decode("utf-8")))
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            logger.error("Failed to load Google service account: %s", e)
            logger.error(
                "See https://console.cloud.google.com/projectselector2/iam-admin/serviceaccounts?supportedpurview=project"
            )
            return
        # pylint: disable=broad-except
        except Exception as e:
            logger.error("Unexpected error loading Google service account: %s", e)
            return

        Secret.objects.update_or_create(
            name=GOOGLE_SERVICE_ACCOUNT_SECRET_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "Google service account credentials.",
                "user_profile": self.user_profile,
            },
        )

    def initialize_provider_models(self, provider: Provider, bearer_token: str, default_model: str):
        """
        Initialize models by fetching them from the OpenAI compatible API end point.

        Example response::

            {
                "object": "list",
                "data": [
                    {
                        "id": "gpt-4-0613",
                        "object": "model",
                        "created": 1686588896,
                        "owned_by": "openai"
                    }
                ]
            }
        """
        log_prefix = f"initialize_provider_models({provider.name}):"
        self.stdout.write("-" * 80)
        end_point = "models"
        url = urljoin(provider.base_url, end_point)
        headers = {"Authorization": f"Bearer {bearer_token}"}

        try:
            self.stdout.write(f"{log_prefix} Fetching provider models from {url}")
            response = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException as e:
            self.stdout.write(self.style.ERROR(f"{log_prefix} Failed to fetch provider models. Error: {e}"))
            return

        if response.status_code == HTTPStatus.NOT_FOUND:
            self.stdout.write(
                self.style.WARNING(f"{log_prefix} Provider models endpoint not found for this provider: {url}")
            )
            return

        if response.status_code != HTTPStatus.OK:
            try:
                error_message = response.json().get("error", {}).get("message", response.text)
            # pylint: disable=broad-except
            except Exception:
                error_message = response.text
            self.stdout.write(
                self.style.ERROR(
                    f"{log_prefix} Failed to fetch provider models. {url} Response {response.status_code}: {error_message}"
                )
            )
            return

        models = response.json().get("data", [])
        if len(models) == 0:
            self.stdout.write(self.style.WARNING(f"{log_prefix} No provider models found."))
            return

        self.stdout.write(f"{log_prefix} Found {len(models)} provider models.")

        for model in models:
            model_name = model.get("id")
            if model_name:
                self.initialize_provider_model(
                    provider=provider, model_name=model_name, is_default=model_name == default_model
                )
        self.stdout.write(
            self.style.SUCCESS(f"{log_prefix} provider models initialized {len(models)} models successfully.")
        )

    def initialize_provider_model(self, provider: Provider, model_name: str, is_default: bool = False):
        """Helper function to initialize a single provider model."""

        ProviderModel.objects.update_or_create(
            provider=provider,
            name=model_name,
            defaults={
                "description": f"{model_name} model for {provider.name}.",
                "is_active": True,
                "is_default": is_default,
            },
        )

    def initialize_anthropic(self):
        """Initialize Anthropic provider and its models."""
        API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
        NAME = "anthropic"
        DEFAULT_MODEL = "claude-sonnet-4-6"
        API_KEY_NAME = "anthropic_api_key"

        logger.info("initialize_anthropic")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_anthropic: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_anthropic: {API_KEY_ENV_VAR} is not set. Cannot initialize Anthropic provider."
                    f"Get your API key from https://platform.claude.com/docs/en/api/overview and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        secret, _ = Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for Anthropic services.",
                "user_profile": self.user_profile,
            },
        )

        provider, _ = Provider.objects.update_or_create(
            name=NAME,
            defaults={
                "description": "Anthropic provides advanced AI models and APIs.",
                "user_profile": self.user_profile,
                "status": ProviderStatus.VERIFIED,
                "is_active": True,
                "is_verified": True,
                "is_deprecated": False,
                "is_flagged": False,
                "is_suspended": False,
                "base_url": "https://api.anthropic.com/v1/",
                "api_key": secret,
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://www.anthropic.com/",
                "contact_email": SMARTER_CONTACT_EMAIL,
                "contact_email_verified": timezone.now(),
                "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                "support_email_verified": timezone.now(),
                "terms_of_service_url": "https://privacy.claude.com/en/articles/9190861-terms-of-service-updates/",
                "privacy_policy_url": "https://privacy.claude.com/en/",
                "docs_url": "https://platform.claude.com/docs/en/api/overview",
                "tos_accepted_at": timezone.now(),
                "tos_accepted_by": self.user_profile.cached_user,
            },
        )
        filename = "anthropic-logo.jpeg"
        anthropic_logo = HERE / "data" / "logos" / "anthropic" / filename
        with open(anthropic_logo, "rb") as logo_file:
            provider.logo.save(filename, ContentFile(logo_file.read()), save=True)

        self.initialize_provider_models(
            provider=provider,
            bearer_token=secret_string.get_secret_value(),
            default_model=DEFAULT_MODEL,
        )

    def initialize_cohere(self):
        """Initialize Cohere provider and its models."""
        API_KEY_ENV_VAR = "COHERE_API_KEY"
        NAME = "cohere"
        DEFAULT_MODEL = "command-r-plus"
        API_KEY_NAME = "cohere_api_key"

        logger.info("initialize_cohere")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_cohere: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_cohere: {API_KEY_ENV_VAR} is not set. Cannot initialize Cohere provider."
                    f"Get your API key from https://docs.cohere.com/docs/ and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        secret, _ = Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for Cohere services.",
                "user_profile": self.user_profile,
            },
        )

        provider, _ = Provider.objects.update_or_create(
            name=NAME,
            defaults={
                "description": "Cohere provides advanced AI models and APIs.",
                "user_profile": self.user_profile,
                "status": ProviderStatus.VERIFIED,
                "is_active": True,
                "is_verified": True,
                "is_deprecated": False,
                "is_flagged": False,
                "is_suspended": False,
                "base_url": "https://api.cohere.com/v1/",
                "api_key": secret,
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://www.cohere.com/",
                "contact_email": SMARTER_CONTACT_EMAIL,
                "contact_email_verified": timezone.now(),
                "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                "support_email_verified": timezone.now(),
                "terms_of_service_url": "https://www.cohere.com/terms-of-service",
                "privacy_policy_url": "https://www.cohere.com/privacy",
                "docs_url": "https://platform.cohere.com/docs/en/api/overview",
                "tos_accepted_at": timezone.now(),
                "tos_accepted_by": self.user_profile.cached_user,
            },
        )
        filename = "cohere-logo.png"
        cohere_logo = HERE / "data" / "logos" / "cohere" / filename
        with open(cohere_logo, "rb") as logo_file:
            provider.logo.save(filename, ContentFile(logo_file.read()), save=True)

        self.initialize_provider_models(
            provider=provider,
            bearer_token=secret_string.get_secret_value(),
            default_model=DEFAULT_MODEL,
        )

    def initialize_fireworks(self):
        """Initialize Fireworks provider and its models."""
        API_KEY_ENV_VAR = "FIREWORKS_API_KEY"
        NAME = "fireworks"
        DEFAULT_MODEL = "command-r-plus"
        API_KEY_NAME = "fireworks_api_key"

        logger.info("initialize_fireworks")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_fireworks: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_fireworks: {API_KEY_ENV_VAR} is not set. Cannot initialize Fireworks provider."
                    f"Get your API key from https://app.fireworks.ai/settings/users/api-keys and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        secret, _ = Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for Fireworks services.",
                "user_profile": self.user_profile,
            },
        )

        provider, _ = Provider.objects.update_or_create(
            name=NAME,
            defaults={
                "description": "Fireworks provides advanced AI models and APIs.",
                "user_profile": self.user_profile,
                "status": ProviderStatus.VERIFIED,
                "is_active": True,
                "is_verified": True,
                "is_deprecated": False,
                "is_flagged": False,
                "is_suspended": False,
                "base_url": "https://api.fireworks.ai/inference/v1/",
                "api_key": secret,
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://www.fireworks.ai/",
                "contact_email": SMARTER_CONTACT_EMAIL,
                "contact_email_verified": timezone.now(),
                "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                "support_email_verified": timezone.now(),
                "terms_of_service_url": "https://fireworks.ai/terms-of-service",
                "privacy_policy_url": "https://fireworks.ai/privacy-policy",
                "docs_url": "https://docs.fireworks.com/docs/en/api/overview",
                "tos_accepted_at": timezone.now(),
                "tos_accepted_by": self.user_profile.cached_user,
            },
        )
        filename = "fireworks-logo.jpeg"
        fireworks_logo = HERE / "data" / "logos" / "fireworks" / filename
        with open(fireworks_logo, "rb") as logo_file:
            provider.logo.save(filename, ContentFile(logo_file.read()), save=True)

        self.initialize_provider_models(
            provider=provider,
            bearer_token=secret_string.get_secret_value(),
            default_model=DEFAULT_MODEL,
        )

    def initialize_googleai(self):
        """Initialize Google AI provider and its models."""
        API_KEY_ENV_VAR = "GEMINI_API_KEY"
        NAME = "googleai"
        DEFAULT_MODEL = "gemini-flash-latest"
        API_KEY_NAME = "googleai_api_key"

        logger.info("initialize_googleai")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_googleai: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_googleai: {API_KEY_ENV_VAR} is not set. Cannot initialize Google AI provider."
                    f"Get your API key from https://aistudio.google.com/app/apikey and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        secret, _ = Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for Google AI services.",
                "user_profile": self.user_profile,
            },
        )

        provider, _ = Provider.objects.update_or_create(
            name=NAME,
            defaults={
                "description": "Google AI provides a range of AI and machine learning services.",
                "user_profile": self.user_profile,
                "status": ProviderStatus.VERIFIED,
                "is_active": True,
                "is_verified": True,
                "is_deprecated": False,
                "is_flagged": False,
                "is_suspended": False,
                "base_url": "https://generativelanguage.googleapis.com/v1beta/",
                "api_key": secret,
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "prompt/completions",
                "website_url": "https://ai.google.com/",
                "contact_email": SMARTER_CONTACT_EMAIL,
                "contact_email_verified": timezone.now(),
                "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                "support_email_verified": timezone.now(),
                "terms_of_service_url": "https://cloud.google.com/terms/",
                "privacy_policy_url": "https://policies.google.com/privacy",
                "docs_url": "https://developers.generativeai.google/learn/api",
                "tos_accepted_at": timezone.now(),
                "tos_accepted_by": self.user_profile.cached_user,
            },
        )
        filename = "google-ai.png"
        google_logo = HERE / "data" / "logos" / "googleai" / filename
        with open(google_logo, "rb") as logo_file:
            provider.logo.save(filename, ContentFile(logo_file.read()), save=True)

        bearer_token = get_google_service_account_bearer_token()
        if not bearer_token:
            self.stdout.write(
                self.style.ERROR(
                    "initialize_googleai: Failed to obtain Google service account bearer token. Cannot initialize Google AI provider models."
                )
            )
            return
        self.initialize_provider_models(provider=provider, bearer_token=bearer_token, default_model=DEFAULT_MODEL)

    def initialize_google_maps(self):
        """Initialize Google Maps provider."""
        API_KEY_ENV_VAR = "GOOGLE_MAPS_API_KEY"
        API_KEY_NAME = GOOGLE_MAPS_API_KEY_SECRET_NAME

        logger.info("initialize_googlemaps")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_googlemaps: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_googlemaps: {API_KEY_ENV_VAR} is not set. Cannot initialize Google Maps provider."
                    f"Get your API key from https://aistudio.google.com/app/apikey and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for Google Maps services.",
                "user_profile": self.user_profile,
            },
        )

    def initialize_metaai(self):
        """Initialize Meta AI provider and its models."""
        API_KEY_ENV_VAR = "LLAMA_API_KEY"
        NAME = "metaai"
        DEFAULT_MODEL = "llama3.2-3b"
        API_KEY_NAME = "metaai_api_key"

        logger.info("initialize_metaai")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_metaai: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_metaai: {API_KEY_ENV_VAR} is not set. Cannot initialize Meta AI provider."
                    f"Get your API key from https://llama.developer.meta.com/ and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        secret, _ = Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for Meta AI services.",
                "user_profile": self.user_profile,
            },
        )

        provider, _ = Provider.objects.update_or_create(
            name=NAME,
            defaults={
                "description": "Meta AI provides a range of AI and machine learning services.",
                "user_profile": self.user_profile,
                "status": ProviderStatus.VERIFIED,
                "is_active": False,
                "is_verified": False,
                "is_deprecated": False,
                "is_flagged": False,
                "is_suspended": False,
                "base_url": "https://metaai.com/api/",
                "api_key": secret,
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://ai.meta.com/",
                "contact_email": SMARTER_CONTACT_EMAIL,
                "contact_email_verified": timezone.now(),
                "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                "support_email_verified": timezone.now(),
                "terms_of_service_url": "https://ai.meta.com/terms/",
                "privacy_policy_url": "https://ai.meta.com/privacy/",
                "docs_url": "https://ai.meta.com/docs/",
                "tos_accepted_at": timezone.now(),
                "tos_accepted_by": self.user_profile.cached_user,
            },
        )

        filename = "Meta_lockup_mono_white_RGB.svg"
        meta_logo = HERE / "data" / "logos" / "metaai" / "mono_white" / filename
        with open(meta_logo, "rb") as logo_file:
            provider.logo.save(filename, ContentFile(logo_file.read()), save=True)

        self.initialize_provider_models(
            provider=provider,
            bearer_token=secret_string.get_secret_value(),
            default_model=DEFAULT_MODEL,
        )

    def initialize_mistral(self):
        """Initialize Mistral provider and its models."""
        API_KEY_ENV_VAR = "MISTRAL_API_KEY"
        NAME = "mistral"
        DEFAULT_MODEL = "mistral-1"
        API_KEY_NAME = "mistral_api_key"

        logger.info("initialize_mistral")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_mistral: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_mistral: {API_KEY_ENV_VAR} is not set. Cannot initialize Mistral provider."
                    f"Get your API key from https://admin.mistral.ai/organization/api-keys and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        secret, _ = Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for Mistral AI services.",
                "user_profile": self.user_profile,
            },
        )

        provider, _ = Provider.objects.update_or_create(
            name=NAME,
            defaults={
                "description": "Mistral AI provides a range of AI and machine learning services.",
                "user_profile": self.user_profile,
                "status": ProviderStatus.VERIFIED,
                "is_active": False,
                "is_verified": False,
                "is_deprecated": False,
                "is_flagged": False,
                "is_suspended": False,
                "base_url": "https://api.mistral.ai/v1/",
                "api_key": secret,
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://mistral.ai/",
                "contact_email": SMARTER_CONTACT_EMAIL,
                "contact_email_verified": timezone.now(),
                "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                "support_email_verified": timezone.now(),
                "terms_of_service_url": "https://legal.mistral.ai/terms/",
                "privacy_policy_url": "https://legal.mistral.ai/terms/privacy-policy/",
                "docs_url": "https://docs.mistral.ai/",
                "tos_accepted_at": timezone.now(),
                "tos_accepted_by": self.user_profile.cached_user,
            },
        )

        filename = "mistral-logo.jpeg"
        mistral_logo = HERE / "data" / "logos" / "mistral" / filename
        with open(mistral_logo, "rb") as logo_file:
            provider.logo.save(filename, ContentFile(logo_file.read()), save=True)

        self.initialize_provider_models(
            provider=provider,
            bearer_token=secret_string.get_secret_value(),
            default_model=DEFAULT_MODEL,
        )

    def initialize_openai(self):
        """Initialize OpenAI provider and its models."""
        API_KEY_ENV_VAR = "OPENAI_API_KEY"
        NAME = "openai"
        DEFAULT_MODEL = "gpt-4o-mini"
        API_KEY_NAME = "openai_api_key"

        logger.info("initialize_openai")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_openai: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_openai: {API_KEY_ENV_VAR} is not set. Cannot initialize OpenAI provider."
                    f"Get your API key from https://platform.openai.com/api-keys and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        secret, _ = Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for OpenAI services.",
                "user_profile": self.user_profile,
            },
        )

        provider, _ = Provider.objects.update_or_create(
            name=NAME,
            defaults={
                "description": "OpenAI provides advanced AI models and APIs.",
                "user_profile": self.user_profile,
                "status": ProviderStatus.VERIFIED,
                "is_active": True,
                "is_verified": True,
                "is_deprecated": False,
                "is_flagged": False,
                "is_suspended": False,
                "base_url": "https://api.openai.com/v1/",
                "api_key": secret,
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "prompt/completions",
                "website_url": "https://www.openai.com/",
                "contact_email": SMARTER_CONTACT_EMAIL,
                "contact_email_verified": timezone.now(),
                "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                "support_email_verified": timezone.now(),
                "terms_of_service_url": "https://openai.com/policies/terms-of-use/",
                "privacy_policy_url": "https://openai.com/policies/privacy-policy/",
                "docs_url": "https://developers.openai.com/api/reference/overview",
                "tos_accepted_at": timezone.now(),
                "tos_accepted_by": self.user_profile.cached_user,
            },
        )
        filename = "OpenAI-white-monoblossom.png"
        openai_logo = HERE / "data" / "logos" / "openai" / filename
        with open(openai_logo, "rb") as logo_file:
            provider.logo.save(filename, ContentFile(logo_file.read()), save=True)

        self.initialize_provider_models(
            provider=provider,
            bearer_token=secret_string.get_secret_value(),
            default_model=DEFAULT_MODEL,
        )

    def initialize_togetheria(self):
        """Initialize TogetherAI provider and its models."""
        API_KEY_ENV_VAR = "TOGETHERAI_API_KEY"
        NAME = "togetherai"
        DEFAULT_MODEL = "gpt-4o-mini"
        API_KEY_NAME = "togetherai_api_key"

        logger.info("initialize_togetherai")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_togetherai: User profile is not set."))
            return

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_togetherai: {API_KEY_ENV_VAR} is not set. Cannot initialize TogetherAI provider."
                    f"Get your API key from https://platform.openai.com/api-keys and add it to your .env file as {API_KEY_ENV_VAR}."
                )
            )
            return

        secret, _ = Secret.objects.update_or_create(
            name=API_KEY_NAME,
            encrypted_value=Secret.encrypt(secret_string.get_secret_value()),
            defaults={
                "description": "API key for TogetherAI services.",
                "user_profile": self.user_profile,
            },
        )

        provider, _ = Provider.objects.update_or_create(
            name=NAME,
            defaults={
                "description": "TogetherAI provides advanced AI models and APIs.",
                "user_profile": self.user_profile,
                "status": ProviderStatus.VERIFIED,
                "is_active": True,
                "is_verified": True,
                "is_deprecated": False,
                "is_flagged": False,
                "is_suspended": False,
                "base_url": "https://api.togai.com/v1/",
                "api_key": secret,
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://www.together.ai/",
                "contact_email": SMARTER_CONTACT_EMAIL,
                "contact_email_verified": timezone.now(),
                "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                "support_email_verified": timezone.now(),
                "terms_of_service_url": "https://www.together.ai/terms-of-service/",
                "privacy_policy_url": "https://docs.together.ai/docs/privacy-and-security",
                "docs_url": "https://docs.together.ai/",
                "tos_accepted_at": timezone.now(),
                "tos_accepted_by": self.user_profile.cached_user,
            },
        )
        filename = "together-logo.jpeg"
        togetherai_logo = HERE / "data" / "logos" / "togetherai" / filename
        with open(togetherai_logo, "rb") as logo_file:
            provider.logo.save(filename, ContentFile(logo_file.read()), save=True)

        self.initialize_provider_models(
            provider=provider,
            bearer_token=secret_string.get_secret_value(),
            default_model=DEFAULT_MODEL,
        )

    def handle(self, *args, **options):
        """Initialize all built-in providers."""
        self.handle_begin()

        try:
            self.user_profile = smarter_cached_objects.smarter_admin_user_profile
            self.initialize_anthropic()
            self.initialize_cohere()
            self.initialize_fireworks()
            self.initialize_google_service_account()
            self.initialize_googleai()
            self.initialize_google_maps()
            self.initialize_metaai()
            self.initialize_mistral()
            self.initialize_openai()
            self.initialize_togetheria()
        # pylint: disable=broad-except
        except Exception as exc:
            self.handle_completed_failure(msg=f"initialize_providers: Error initializing providers: {exc}")
            return

        self.handle_completed_success()
