"""This module is used to generate seed records for the chat history models."""

import logging
from http import HTTPStatus
from pathlib import Path
from urllib.parse import urljoin

import google.auth.transport.requests
import requests
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone
from google.auth.exceptions import GoogleAuthError
from google.oauth2 import service_account

from smarter.apps.account.models import Secret, UserProfile
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.provider.models import Provider, ProviderModel, ProviderStatus
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CONTACT_EMAIL, SMARTER_CUSTOMER_SUPPORT_EMAIL


logger = logging.getLogger(__name__)

HERE = Path(__file__).resolve().parent

OPENAI_API = "OpenAI"
OPENAI_DEFAULT_MODEL = "gpt-4-turbo"
OPENAI_API_KEY_NAME = "openai_api_key"

GOOGLE_API = "GoogleAI"
GOOGLE_DEFAULT_MODEL = "gemini-2.0-flash"
GOOGLE_API_KEY_NAME = "google_ai_api_key"

META_API = "MetaAI"
META_DEFAULT_MODEL = "llama3.1-70b"
META_API_KEY_NAME = "meta_ai_api_key"


class Command(BaseCommand):
    """
    Django manage.py initialize_providers.py command.
    This command is used to create/update the principal
    Providers that are preloaded on all platforms.

    This runs during deployment.
    """

    user_profile: UserProfile | None = None

    def initialize_provider_models(self, provider: Provider, bearer_token: str, default_model: str):
        """
        Initialize models by fetching them from the OpenAI compatible API end point.
        example response:
        {
            "object": "list",
            "data": [
                {
                    "id": "gpt-4-0613",
                    "object": "model",
                    "created": 1686588896,
                    "owned_by": "openai"
                },
            ]
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
        """
        helper function to initialize a single provider model.
        """

        ProviderModel.objects.update_or_create(
            provider=provider,
            name=model_name,
            defaults={
                "description": f"{model_name} model for {provider.name}.",
                "is_active": True,
                "is_default": is_default,
            },
        )

    def initialize_openai(self):
        """
        Initialize OpenAI provider and its models.
        """
        logger.info("initialize_openai")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_openai: User profile is not set."))
            return

        openai_api_key, _ = Secret.objects.update_or_create(
            name=OPENAI_API_KEY_NAME,
            defaults={
                "description": "API key for OpenAI services.",
                "user_profile": self.user_profile,
                "encrypted_value": Secret.encrypt(smarter_settings.openai_api_key.get_secret_value()),
            },
        )

        filename = "OpenAI-white-monoblossom.png"
        openai_logo = HERE / "data" / "logos" / "openai" / filename
        with open(openai_logo, "rb") as logo_file:
            provider, _ = Provider.objects.update_or_create(
                name=OPENAI_API,
                defaults={
                    "description": "OpenAI provides advanced AI models and APIs.",
                    "owner": self.user_profile.user,
                    "account": self.user_profile.account,
                    "status": ProviderStatus.VERIFIED,
                    "is_active": True,
                    "is_verified": True,
                    "is_deprecated": False,
                    "is_flagged": False,
                    "is_suspended": False,
                    "base_url": "https://api.openai.com/v1/",
                    "api_key": openai_api_key,
                    "connectivity_test_path": "chat/completions",
                    "logo": ContentFile(logo_file.read(), name=filename),
                    "website_url": "https://www.openai.com/",
                    "contact_email": SMARTER_CONTACT_EMAIL,
                    "contact_email_verified": timezone.now(),
                    "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                    "support_email_verified": timezone.now(),
                    "terms_of_service_url": "https://openai.com/policies/terms-of-use/",
                    "privacy_policy_url": "https://openai.com/policies/privacy-policy/",
                    "docs_url": "https://platform.openai.com/docs/api-reference",
                    "tos_accepted_at": timezone.now(),
                    "tos_accepted_by": self.user_profile.user,
                },
            )

            self.initialize_provider_models(
                provider=provider,
                bearer_token=smarter_settings.openai_api_key.get_secret_value(),
                default_model=OPENAI_DEFAULT_MODEL,
            )

    def initialize_googleai(self):
        """
        Initialize Google AI provider and its models.
        """
        logger.info("initialize_googleai")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_googleai: User profile is not set."))
            return

        googleai_api_key, _ = Secret.objects.update_or_create(
            name=GOOGLE_API_KEY_NAME,
            defaults={
                "description": "API key for Google AI services.",
                "user_profile": self.user_profile,
                "encrypted_value": Secret.encrypt(smarter_settings.gemini_api_key.get_secret_value()),
            },
        )

        SCOPES = [
            "https://www.googleapis.com/auth/cloud-platform",
            "https://www.googleapis.com/auth/generative-language.retriever",
            "https://www.googleapis.com/auth/generative-language",
        ]

        try:
            credentials = service_account.Credentials.from_service_account_info(
                smarter_settings.google_service_account, scopes=SCOPES
            )
            auth_req = google.auth.transport.requests.Request()
        except GoogleAuthError as e:
            self.stdout.write(self.style.ERROR(f"initialize_googleai: Error loading Google credentials: {e}"))
            return
        credentials.refresh(auth_req)
        bearer_token = credentials.token

        filename = "google-ai.png"
        google_logo = HERE / "data" / "logos" / "googleai" / filename
        with open(google_logo, "rb") as logo_file:
            provider, _ = Provider.objects.update_or_create(
                name=GOOGLE_API,
                defaults={
                    "description": "Google AI provides a range of AI and machine learning services.",
                    "owner": self.user_profile.user,
                    "account": self.user_profile.account,
                    "status": ProviderStatus.VERIFIED,
                    "is_active": True,
                    "is_verified": True,
                    "is_deprecated": False,
                    "is_flagged": False,
                    "is_suspended": False,
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/",
                    "api_key": googleai_api_key,
                    "connectivity_test_path": "chat/completions",
                    "logo": ContentFile(logo_file.read(), name=filename),
                    "website_url": "https://ai.google.com/",
                    "contact_email": SMARTER_CONTACT_EMAIL,
                    "contact_email_verified": timezone.now(),
                    "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                    "support_email_verified": timezone.now(),
                    "terms_of_service_url": "https://cloud.google.com/terms/",
                    "privacy_policy_url": "https://policies.google.com/privacy",
                    "docs_url": "https://developers.generativeai.google/learn/api",
                    "tos_accepted_at": timezone.now(),
                    "tos_accepted_by": self.user_profile.user,
                },
            )
            self.initialize_provider_models(
                provider=provider, bearer_token=bearer_token, default_model=GOOGLE_DEFAULT_MODEL
            )

    def initialize_metaai(self):
        """
        Initialize Meta AI provider and its models.
        """
        logger.info("initialize_metaai")
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR("initialize_metaai: User profile is not set."))
            return

        metaai_api_key, _ = Secret.objects.update_or_create(
            name=META_API_KEY_NAME,
            defaults={
                "description": "API key for Meta AI services.",
                "user_profile": self.user_profile,
                "encrypted_value": Secret.encrypt(smarter_settings.llama_api_key.get_secret_value()),
            },
        )
        filename = "Meta_lockup_mono_white_RGB.svg"
        meta_logo = HERE / "data" / "logos" / "metaai" / "mono_white" / filename

        with open(meta_logo, "rb") as logo_file:
            provider, _ = Provider.objects.update_or_create(
                name=META_API,
                defaults={
                    "description": "Meta AI provides a range of AI and machine learning services.",
                    "owner": self.user_profile.user,
                    "account": self.user_profile.account,
                    "status": ProviderStatus.VERIFIED,
                    "is_active": True,
                    "is_verified": True,
                    "is_deprecated": False,
                    "is_flagged": False,
                    "is_suspended": False,
                    "base_url": "https://metaai.com/api/",
                    "api_key": metaai_api_key,
                    "connectivity_test_path": "chat/completions",
                    "logo": ContentFile(logo_file.read(), name=filename),
                    "website_url": "https://ai.meta.com/",
                    "contact_email": SMARTER_CONTACT_EMAIL,
                    "contact_email_verified": timezone.now(),
                    "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
                    "support_email_verified": timezone.now(),
                    "terms_of_service_url": "https://ai.meta.com/terms/",
                    "privacy_policy_url": "https://ai.meta.com/privacy/",
                    "docs_url": "https://ai.meta.com/docs/",
                    "tos_accepted_at": timezone.now(),
                    "tos_accepted_by": self.user_profile.user,
                },
            )
            self.initialize_provider_models(
                provider=provider,
                bearer_token=smarter_settings.llama_api_key.get_secret_value(),
                default_model=META_DEFAULT_MODEL,
            )

    def handle(self, *args, **options):
        """
        Initialize all built-in providers.
        """
        self.stdout.write(self.style.NOTICE("smarter.apps.provider.management.commands.initialize_providers started."))

        try:
            self.user_profile = get_cached_smarter_admin_user_profile()
            self.initialize_openai()
            self.initialize_googleai()
            self.initialize_metaai()
        # pylint: disable=broad-except
        except Exception as exc:
            self.stdout.write(self.style.ERROR(f"initialize_providers: Error initializing providers: {exc}"))
            self.stdout.write(
                self.style.ERROR(
                    "smarter.apps.provider.management.commands.initialize_providers completed with errors."
                )
            )
            return

        self.stdout.write(
            self.style.SUCCESS("smarter.apps.provider.management.commands.initialize_providers completed successfully.")
        )
