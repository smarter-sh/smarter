"""This module is used to generate seed records for the chat history models."""

from http import HTTPStatus
from pathlib import Path
from urllib.parse import urljoin

import requests
from django.core.management.base import BaseCommand
from django.utils import timezone

from smarter.apps.account.models import Secret, UserProfile
from smarter.apps.account.utils import get_cached_smarter_admin_user_profile
from smarter.apps.provider.models import Provider, ProviderModel, ProviderStatus
from smarter.common.conf import settings as smarter_settings
from smarter.common.const import SMARTER_CONTACT_EMAIL, SMARTER_CUSTOMER_SUPPORT_EMAIL


HERE = Path(__file__).resolve().parent

OPENAI_API = "OpenAI"
OPENAI_DEFAULT_MODEL = "gpt-4o-mini"
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

    def initialize_provider_models(self, provider: Provider, default_model: str):
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
        end_point = "v1/models"
        url = urljoin(provider.base_url, end_point)
        headers = {"Authorization": f"Bearer {smarter_settings.openai_api_key.get_secret_value()}"}

        try:
            response = requests.get(url, headers=headers, timeout=10)
        except requests.RequestException as e:
            self.stdout.write(
                self.style.ERROR(f"initialize_provider_models: Failed to fetch OpenAI models. Error: {e}")
            )
            return
        if response.status_code != HTTPStatus.OK:
            self.stdout.write(
                self.style.ERROR(
                    f"initialize_provider_models: Failed to fetch OpenAI models. Status code: {response.status_code}"
                )
            )
            return

        models = response.json().get("data", [])
        if len(models) == 0:
            self.stdout.write(
                self.style.WARNING(
                    "initialize_provider_models: No OpenAI models found. Please check your API key and network connection."
                )
            )
            return

        self.stdout.write(f"initialize_provider_models: Found {len(models)} OpenAI models.")

        for model in models:
            model_name = model.get("id")
            if model_name:
                self.initialize_provider_model(
                    provider=provider, model_name=model_name, is_default=model_name == default_model
                )
        self.stdout.write(
            self.style.SUCCESS(
                f"initialize_provider_models: OpenAI models initialized {len(models)} models successfully."
            )
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
                "status": ProviderStatus.VERIFIED,
                "is_active": True,
                "is_default": is_default,
            },
        )

    def initialize_openai(self):
        """
        Initialize OpenAI provider and its models.
        """
        openai_api_key, _ = Secret.objects.update_or_create(
            name=OPENAI_API_KEY_NAME,
            defaults={
                "description": "API key for OpenAI services.",
                "user_profile": self.user_profile,
                "encrypted_value": Secret.encrypt("your-openai-api-key"),
            },
        )

        openai_logo = HERE / "data" / "logos" / "openai" / "OpenAI-white-monoblossom.png"
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
                    "logo": logo_file.read(),
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

            self.initialize_provider_models(provider=provider, default_model=OPENAI_DEFAULT_MODEL)

    def initialize_googleai(self):
        """
        Initialize Google AI provider and its models.
        """
        googleai_api_key, _ = Secret.objects.update_or_create(
            name=GOOGLE_API_KEY_NAME,
            defaults={
                "description": "API key for Google AI services.",
                "user_profile": self.user_profile,
                "encrypted_value": Secret.encrypt("your-google-ai-api-key"),
            },
        )

        google_logo = HERE / "data" / "logos" / "googleai" / "google-ai.png"
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
                    "base_url": "https://generativelanguage.googleapis.com/v1beta/openai/",
                    "api_key": googleai_api_key,
                    "connectivity_test_path": "chat/completions",
                    "logo": logo_file.read(),
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
            self.initialize_provider_models(provider=provider, default_model=GOOGLE_DEFAULT_MODEL)

    def initialize_metaai(self):
        """
        Initialize Meta AI provider and its models.
        """
        metaai_api_key, _ = Secret.objects.update_or_create(
            name=META_API_KEY_NAME,
            defaults={
                "description": "API key for Meta AI services.",
                "user_profile": self.user_profile,
                "encrypted_value": Secret.encrypt("your-meta-ai-api-key"),
            },
        )
        meta_logo = HERE / "data" / "logos" / "metaai" / "mono_white" / "Meta_lockup_mono_white_RGB.svg"

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
                    "logo": logo_file.read(),
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
            self.initialize_provider_models(provider=provider, default_model=META_DEFAULT_MODEL)

    def handle(self, *args, **options):
        """
        Initialize all built-in providers.
        """
        self.stdout.write("initialize_providers: Initializing providers...")

        self.user_profile = get_cached_smarter_admin_user_profile()
        self.initialize_openai()
        self.initialize_googleai()
        self.initialize_metaai()

        self.stdout.write(self.style.SUCCESS("initialize_providers: Providers initialized successfully."))
