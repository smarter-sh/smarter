"""Initialize 3rd party providers."""

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

    Used to create/update the principal
    Providers that are preloaded on all platforms. Creates/updates the API key Secret,
    the Provider, and the ProviderModels for each provider.
    The following providers are initialized:

    - Anthropic
    - Cohere
    - Fireworks
    - Google Service Account
    - Google AI
    - Google Maps
    - Meta AI
    - Mistral
    - OpenAI
    - TogetherIA

    This is called indirectly by initialize_platform and runs during automated deployment.
    """

    user_profile: UserProfile

    def initialize_secret(self, secret_string: str, secret_name: str, description: str) -> Secret:
        """
        Initialize a secret from an environment variable.

        Args:
            env_var (str): The name of the environment variable containing the secret value.
            secret_name (str): The name to assign to the created/updated Secret object.
            description (str): A description for the Secret object.
        """
        secret, _ = Secret.objects.update_or_create(
            name=secret_name,
            user_profile=self.user_profile,
            defaults={
                "description": description,
                "encrypted_value": Secret.encrypt(secret_string),
            },
        )
        return secret

    def initialize_google_service_account(self):
        """
        Initialize Google service account credentials.

        A Google service account is a special identity that allows an application,
        rather than a person, to securely authenticate with Google APIs and
        services. It uses cryptographic credentials to prove its identity and
        obtain temporary access tokens without requiring a user to log in. The
        service account can only perform the actions that have been explicitly
        granted to it through Google Cloud IAM permissions.

        Example service account JSON structure::

            service_account_json = {
            "type": "service_account",
            "project_id": "smarter-sh",
            "private_key_id": "65fc3e5bd38b1234567890676f6d6abcdefghijk",
            "private_key": "PRIVATE-KEY-DATA",
            "client_email": "smarter-gemini-initializer@smarter-sh.iam.gserviceaccount.com",
            "client_id": "104887368144732193269",
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": "https://www.googleapis.com/robot/v1/metadata/x509/smarter-gemini-initializer%40smarter-sh.iam.gserviceaccount.com",
            "universe_domain": "googleapis.com"
            }

            service_account_b64 = base64.b64encode(json.dumps(service_account_json).encode("utf-8")).decode("ascii")
            print(service_account_b64)
        """
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

        self.initialize_secret(
            secret_string=secret_string.get_secret_value(),
            secret_name=GOOGLE_SERVICE_ACCOUNT_SECRET_NAME,
            description="Google service account credentials.",
        )

    def initialize_generic_provider(
        self,
        api_key_env_var: str,
        name: str,
        provider_configuration: dict,
        logo_filename: str,
        provider_api_url: str,
    ):
        """
        Initialize a provider and its models.

        - create/update api key secret
        - create/update provider
        - create/update provider models
        """

        def _initialize_provider_models(provider: Provider, bearer_token: str, default_model: str):
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
            log_prefix = f"_initialize_provider_models({provider.name}):"
            self.stdout.write("-" * 80)
            end_point = "models"
            url = urljoin(provider.base_url, end_point)
            headers = {"Authorization": f"Bearer {bearer_token}"}

            def _initialize_provider_model(provider: Provider, model_name: str, is_default: bool = False):
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
                    _initialize_provider_model(
                        provider=provider, model_name=model_name, is_default=model_name == default_model
                    )
            self.stdout.write(
                self.style.SUCCESS(f"{log_prefix} provider models initialized {len(models)} models successfully.")
            )

        logger.info("initialize_%s", name)
        if self.user_profile is None:
            self.stdout.write(self.style.ERROR(f"initialize_{name}: User profile is not set."))
            return

        COMMON_DEFAULTS = {
            "user_profile": self.user_profile,
            "status": ProviderStatus.VERIFIED,
            "is_active": True,
            "is_verified": True,
            "is_deprecated": False,
            "is_flagged": False,
            "is_suspended": False,
            "contact_email": SMARTER_CONTACT_EMAIL,
            "contact_email_verified": timezone.now(),
            "support_email": SMARTER_CUSTOMER_SUPPORT_EMAIL,
            "support_email_verified": timezone.now(),
            "tos_accepted_at": timezone.now(),
            "tos_accepted_by": self.user_profile.user,
        }
        secret_string = SecretStr(get_env(api_key_env_var, is_secret=True, is_required=True))
        if not secret_string or not secret_string.get_secret_value():
            self.stdout.write(
                self.style.WARNING(
                    f"initialize_{name}: {api_key_env_var} is not set. Cannot initialize {name} provider."
                    f"Get your API key from {provider_api_url} and add it to your .env file as {api_key_env_var}."
                )
            )
            return

        secret = self.initialize_secret(
            secret_string=secret_string.get_secret_value(),
            secret_name=api_key_env_var.lower(),
            description=f"API key for {name} services.",
        )
        provider, _ = Provider.objects.update_or_create(
            name=name,
            defaults={
                **COMMON_DEFAULTS,
                **provider_configuration,
                "api_key": secret,
            },
        )
        logo_path = HERE / "data" / "logos" / name / logo_filename
        with open(logo_path, "rb") as logo_file:
            provider.logo.save(logo_filename, ContentFile(logo_file.read()), save=True)

        _initialize_provider_models(
            provider=provider,
            bearer_token=secret_string.get_secret_value(),
            default_model=provider_configuration["default_model"],
        )

    def initialize_anthropic(self):
        """Initialize Anthropic provider and its models."""
        API_KEY_ENV_VAR = "ANTHROPIC_API_KEY"
        NAME = "anthropic"
        DEFAULT_MODEL = "claude-sonnet-4-6"

        self.initialize_generic_provider(
            api_key_env_var=API_KEY_ENV_VAR,
            name=NAME,
            provider_configuration={
                "description": "Anthropic provides advanced AI models and APIs.",
                "base_url": "https://api.anthropic.com/v1/",
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://www.anthropic.com/",
                "terms_of_service_url": "https://privacy.claude.com/en/articles/9190861-terms-of-service-updates/",
                "privacy_policy_url": "https://privacy.claude.com/en/",
                "docs_url": "https://platform.claude.com/docs/en/api/overview",
            },
            logo_filename="anthropic-logo.svg",
            provider_api_url="https://platform.claude.com/docs/en/api/overview",
        )

    def initialize_cohere(self):
        """Initialize Cohere provider and its models."""
        API_KEY_ENV_VAR = "COHERE_API_KEY"
        NAME = "cohere"
        DEFAULT_MODEL = "command-r-plus"

        self.initialize_generic_provider(
            api_key_env_var=API_KEY_ENV_VAR,
            name=NAME,
            provider_configuration={
                "description": "Cohere provides advanced AI models and APIs.",
                "base_url": "https://api.cohere.com/v1/",
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://www.cohere.com/",
                "terms_of_service_url": "https://www.cohere.com/terms-of-service",
                "privacy_policy_url": "https://www.cohere.com/privacy",
                "docs_url": "https://platform.cohere.com/docs/en/api/overview",
            },
            logo_filename="cohere-logo.svg",
            provider_api_url="https://platform.cohere.com/docs/en/api/overview",
        )

    def initialize_fireworks(self):
        """Initialize Fireworks provider and its models."""
        API_KEY_ENV_VAR = "FIREWORKS_API_KEY"
        NAME = "fireworks"
        DEFAULT_MODEL = "command-r-plus"

        self.initialize_generic_provider(
            api_key_env_var=API_KEY_ENV_VAR,
            name=NAME,
            provider_configuration={
                "description": "Fireworks provides advanced AI models and APIs.",
                "base_url": "https://api.fireworks.ai/inference/v1/",
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://www.fireworks.ai/",
                "terms_of_service_url": "https://fireworks.ai/terms-of-service",
                "privacy_policy_url": "https://fireworks.ai/privacy-policy",
                "docs_url": "https://docs.fireworks.com/docs/en/api/overview",
            },
            logo_filename="fireworks-logo.svg",
            provider_api_url="https://app.fireworks.ai/settings/users/api-keys",
        )

    def initialize_googleai(self):
        """Initialize Google AI provider and its models."""
        API_KEY_ENV_VAR = "GEMINI_API_KEY"
        NAME = "googleai"
        DEFAULT_MODEL = "gemini-flash-latest"

        self.initialize_generic_provider(
            api_key_env_var=API_KEY_ENV_VAR,
            name=NAME,
            provider_configuration={
                "description": "Google AI provides a range of AI and machine learning services.",
                "base_url": "https://generativelanguage.googleapis.com/v1beta/",
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "prompt/completions",
                "website_url": "https://ai.google.com/",
                "terms_of_service_url": "https://cloud.google.com/terms/",
                "privacy_policy_url": "https://policies.google.com/privacy",
                "docs_url": "https://developers.generativeai.google/learn/api",
            },
            logo_filename="google-ai.svg",
            provider_api_url="https://aistudio.google.com/app/apikey",
        )

    def initialize_google_maps(self):
        """Initialize Google Maps provider."""
        NAME = "google maps"
        API_KEY_ENV_VAR = "GOOGLE_MAPS_API_KEY"
        API_KEY_NAME = GOOGLE_MAPS_API_KEY_SECRET_NAME

        secret_string = SecretStr(get_env(API_KEY_ENV_VAR, is_secret=True, is_required=True))

        self.initialize_secret(
            secret_string=secret_string.get_secret_value(),
            secret_name=API_KEY_NAME,
            description=f"API key for {NAME} services.",
        )

    def initialize_metaai(self):
        """Initialize Meta AI provider and its models."""
        API_KEY_ENV_VAR = "LLAMA_API_KEY"
        NAME = "metaai"
        DEFAULT_MODEL = "llama3.2-3b"

        self.initialize_generic_provider(
            api_key_env_var=API_KEY_ENV_VAR,
            name=NAME,
            provider_configuration={
                "description": "Meta AI provides a range of AI and machine learning services.",
                "base_url": "https://metaai.com/api/",
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://ai.meta.com/",
                "terms_of_service_url": "https://ai.meta.com/terms/",
                "privacy_policy_url": "https://ai.meta.com/privacy/",
                "docs_url": "https://ai.meta.com/docs/",
            },
            logo_filename="Meta_lockup_mono_white_RGB.svg",
            provider_api_url="https://llama.developer.meta.com/",
        )

    def initialize_mistral(self):
        """Initialize Mistral provider and its models."""
        API_KEY_ENV_VAR = "MISTRAL_API_KEY"
        NAME = "mistral"
        DEFAULT_MODEL = "mistral-1"

        self.initialize_generic_provider(
            api_key_env_var=API_KEY_ENV_VAR,
            name=NAME,
            provider_configuration={
                "description": "Mistral AI provides a range of AI and machine learning services.",
                "user_profile": self.user_profile,
                "base_url": "https://api.mistral.ai/v1/",
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://mistral.ai/",
                "terms_of_service_url": "https://legal.mistral.ai/terms/",
                "privacy_policy_url": "https://legal.mistral.ai/terms/privacy-policy/",
                "docs_url": "https://docs.mistral.ai/",
            },
            logo_filename="mistral-logo.svg",
            provider_api_url="https://admin.mistral.ai/organization/api-keys",
        )

    def initialize_openai(self):
        """Initialize OpenAI provider and its models."""
        API_KEY_ENV_VAR = "OPENAI_API_KEY"
        NAME = "openai"
        DEFAULT_MODEL = "gpt-4o-mini"

        self.initialize_generic_provider(
            api_key_env_var=API_KEY_ENV_VAR,
            name=NAME,
            provider_configuration={
                "description": "OpenAI provides advanced AI models and APIs.",
                "base_url": "https://api.openai.com/v1/",
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "prompt/completions",
                "website_url": "https://www.openai.com/",
                "terms_of_service_url": "https://openai.com/policies/terms-of-use/",
                "privacy_policy_url": "https://openai.com/policies/privacy-policy/",
                "docs_url": "https://developers.openai.com/api/reference/overview",
            },
            logo_filename="OpenAI-white-monoblossom.png",
            provider_api_url="https://platform.openai.com/api-keys",
        )

    def initialize_togetheria(self):
        """Initialize TogetherAI provider and its models."""
        API_KEY_ENV_VAR = "TOGETHERAI_API_KEY"
        NAME = "togetherai"
        DEFAULT_MODEL = "gpt-4o-mini"

        self.initialize_generic_provider(
            api_key_env_var=API_KEY_ENV_VAR,
            name=NAME,
            provider_configuration={
                "description": "TogetherAI provides advanced AI models and APIs.",
                "base_url": "https://api.togai.com/v1/",
                "default_model": DEFAULT_MODEL,
                "connectivity_test_path": "chat/completions",
                "website_url": "https://www.together.ai/",
                "terms_of_service_url": "https://www.together.ai/terms-of-service/",
                "privacy_policy_url": "https://docs.together.ai/docs/privacy-and-security",
                "docs_url": "https://docs.together.ai/",
            },
            logo_filename="together-logo.svg",
            provider_api_url="https://platform.together.ai/api-keys",
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
