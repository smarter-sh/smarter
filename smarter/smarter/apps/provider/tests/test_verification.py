"""
Test :mod:`smarter.apps.provider.verification`: the checks that verify a Provider, and those.

that verify a ProviderModel's capabilities. The openai client, the provider's connectivity
test and the web page test are mocked, so no request leaves the test.
"""

import os
import unittest
from datetime import timedelta
from unittest.mock import MagicMock, patch

from django.utils import timezone

from smarter.apps.provider.models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderStatus,
    ProviderVerification,
)
from smarter.apps.provider.verification import provider as provider_checks
from smarter.apps.provider.verification import provider_model as model_checks
from smarter.apps.secret.models import Secret

from .test_models import ProviderTestBase

API_KEY = "sk-test-verification"


def record(provider_verification=None, provider_model_verification=None, is_successful=False, **kwargs) -> None:
    """
    Record a verification's result, as set_provider_verification() and set_model_verification() do,.

    but without their signals, whose receivers raise (see TestVerificationSignals).
    """
    verification = provider_verification or provider_model_verification
    verification.is_successful = is_successful
    verification.save()


def completion(content: str) -> MagicMock:
    """Return a chat completion whose first choice's message is ``content``."""
    response = MagicMock()
    response.choices[0].message.content = content
    return response


class TestProviderVerification(ProviderTestBase):
    """Test the Provider checks, and verify_provider(), which runs them."""

    def setUp(self):
        super().setUp()
        self.provider.website_url = "https://example.com/"
        self.provider.terms_of_service_url = "https://example.com/tos"
        self.provider.docs_url = "https://example.com/docs"
        self.provider.privacy_policy_url = "https://example.com/privacy"
        self.provider.contact_email = "contact@example.com"
        self.provider.contact_email_verified = timezone.now()
        self.provider.support_email = "support@example.com"
        self.provider.support_email_verified = timezone.now()
        self.provider.logo = "logos/test.png"
        self.provider.save()
        self.accept_tos(self.provider)
        for patcher in (
            patch.dict(os.environ, {f"{self.provider.name.upper()}_API_KEY": "sk-production"}),
            patch.object(provider_checks, "set_provider_verification", record),
        ):
            patcher.start()
            self.addCleanup(patcher.stop)

    def checks(self):
        return [
            provider_checks.verify_provider_api_connectivity,
            provider_checks.verify_provider_logo,
            provider_checks.verify_provider_contact_email,
            provider_checks.verify_provider_support_email,
            provider_checks.verify_provider_website_url,
            provider_checks.verify_provider_terms_of_service_url,
            provider_checks.verify_provider_privacy_policy_url,
            provider_checks.verify_provider_tos_accepted,
            provider_checks.verify_provider_production_api_key,
        ]

    def test_checks_succeed(self):
        """Test that each check succeeds, records its success, and is then skipped while it is valid."""
        with (
            patch.object(Provider, "test_connectivity", return_value=True),
            patch.object(provider_checks, "test_web_page", return_value=True),
        ):
            for check in self.checks():
                with self.subTest(check=check.__name__):
                    self.assertTrue(check(provider=self.provider))
        self.assertEqual(ProviderVerification.objects.filter(provider=self.provider, is_successful=True).count(), 9)

        # a verification that succeeded an hour ago is still valid, so the check is not run again.
        ProviderVerification.objects.filter(provider=self.provider).update(
            updated_at=timezone.now() - timedelta(hours=1)
        )
        with (
            patch.object(Provider, "test_connectivity", side_effect=AssertionError("not called")),
            patch.object(provider_checks, "test_web_page", side_effect=AssertionError("not called")),
        ):
            for check in self.checks():
                with self.subTest(check=check.__name__, cached=True):
                    self.assertTrue(check(provider=self.provider))

    def test_checks_fail(self):
        """Test the checks that fail when the connectivity or web page test fails, or the logo is not an image."""
        self.provider.logo = "logos/test.txt"
        with (
            patch.object(Provider, "test_connectivity", return_value=False),
            patch.object(provider_checks, "test_web_page", return_value=False),
        ):
            for check in (
                provider_checks.verify_provider_api_connectivity,
                provider_checks.verify_provider_logo,
                provider_checks.verify_provider_website_url,
                provider_checks.verify_provider_terms_of_service_url,
                provider_checks.verify_provider_privacy_policy_url,
            ):
                with self.subTest(check=check.__name__):
                    self.assertFalse(check(provider=self.provider))

    @unittest.expectedFailure
    def test_docs_url(self):
        """
        Expected to fail: verify_provider_docs_url() uses ProviderVerificationTypes.DOCS_URL,.

        which does not exist, so it raises AttributeError, as verify_provider() does after
        the checks before it succeed.
        """
        with patch.object(provider_checks, "test_web_page", return_value=True):
            self.assertTrue(provider_checks.verify_provider_docs_url(provider=self.provider))

    def test_verify_provider_fails(self):
        """Test that a provider that is deprecated, suspended or flagged fails verification, and is deactivated."""
        self.provider.is_deprecated = True
        self.provider.is_suspended = True
        self.provider.is_flagged = True
        self.provider.is_active = True
        self.provider.save()
        provider_checks.verify_provider(self.provider.id)
        provider = Provider.objects.get(pk=self.provider.pk)
        self.assertEqual(provider.status, ProviderStatus.FAILED)
        self.assertFalse(provider.is_active)
        self.assertIsNone(provider_checks.verify_provider(999999999))

    @unittest.expectedFailure
    def test_verify_provider_succeeds(self):
        """
        Test that a provider that passes every check is verified and activated.

        Expected to fail: verify_provider() fails a provider unless provider.can_activate,
        which requires the status VERIFIED, which verify_provider() only sets afterwards,
        so a provider that is not verified already can never be verified. Also, it sends
        provider_activated with provider=, but handle_provider_activated() takes instance.
        """
        with (
            patch.object(Provider, "test_connectivity", return_value=True),
            patch.object(provider_checks, "test_web_page", return_value=True),
        ):
            provider_checks.verify_provider(self.provider.id)
        provider = Provider.objects.get(pk=self.provider.pk)
        self.assertEqual(provider.status, ProviderStatus.VERIFIED)
        self.assertTrue(provider.is_active)


class TestProviderModelVerification(ProviderTestBase):
    """Test the ProviderModel checks, with a mocked openai client, and verify_provider_model()."""

    def setUp(self):
        super().setUp()
        secret = Secret.objects.create(
            name=f"test_provider_verification_key_{self.hash_suffix}",
            user_profile=self.user_profile,
            encrypted_value=Secret.encrypt(API_KEY),
        )
        self.addCleanup(Secret.objects.filter(pk=secret.pk).delete)
        self.provider.api_key = secret
        self.provider.save()
        self.model = ProviderModel.objects.create(provider=self.provider, name="gpt-4o")
        patcher = patch.object(model_checks, "openai")
        self.openai = patcher.start()
        self.addCleanup(patcher.stop)
        patcher = patch.object(model_checks, "set_model_verification", record)
        patcher.start()
        self.addCleanup(patcher.stop)
        self.openai.chat.completions.create.return_value = completion("Hola")
        self.openai.chat.completions.create.return_value.__iter__.return_value = iter(["chunk"])

    def reset(self):
        ProviderModelVerification.objects.filter(provider_model=self.model).delete()

    def test_checks_succeed(self):
        """Test the checks that succeed when the openai client does."""
        checks = [
            model_checks.verify_model_streaming,
            model_checks.verify_model_tools,
            model_checks.verify_model_text_input,
            model_checks.verify_model_image_input,
            model_checks.verify_model_audio_input,
            model_checks.verify_model_fine_tuning,
            model_checks.verify_model_code_interpreter,
            model_checks.verify_model_text_to_image,
            model_checks.verify_model_text_to_audio,
            model_checks.verify_model_text_to_text,
            model_checks.verify_model_translation,
        ]
        for check in checks:
            with self.subTest(check=check.__name__):
                self.openai.chat.completions.create.return_value.__iter__.return_value = iter(["chunk"])
                self.assertTrue(check(provider_model=self.model))
                # a verification that succeeded an hour ago is still valid, so the check is not run again.
                ProviderModelVerification.objects.filter(provider_model=self.model).update(
                    updated_at=timezone.now() - timedelta(hours=1)
                )
                self.assertTrue(check(provider_model=self.model))
                self.reset()

    def test_checks_fail(self):
        """Test that each check that calls the openai client fails when the client raises."""
        for method in ("create", "generate"):
            getattr(self.openai.chat.completions, method).side_effect = RuntimeError("unavailable")
        self.openai.images.generate.side_effect = RuntimeError("unavailable")
        self.openai.audio.speech.create.side_effect = RuntimeError("unavailable")
        self.openai.audio.transcriptions.create.side_effect = RuntimeError("unavailable")
        self.openai.fine_tuning.jobs.create.side_effect = RuntimeError("unavailable")
        checks = [
            model_checks.verify_model_streaming,
            model_checks.verify_model_tools,
            model_checks.verify_model_text_input,
            model_checks.verify_model_image_input,
            model_checks.verify_model_audio_input,
            model_checks.verify_model_fine_tuning,
            model_checks.verify_model_text_to_image,
            model_checks.verify_model_text_to_audio,
            model_checks.verify_model_text_to_text,
            model_checks.verify_model_translation,
            model_checks.verify_model_summarization,
            model_checks.verify_model_search,
        ]
        for check in checks:
            with self.subTest(check=check.__name__):
                self.assertFalse(check(provider_model=self.model))
        self.model.name = "not-a-code-interpreter"
        self.assertFalse(model_checks.verify_model_code_interpreter(provider_model=self.model))

    @unittest.expectedFailure
    def test_api_key(self):
        """
        Test that the checks give the openai client the provider's api key.

        Expected to fail: verify_model_streaming(), verify_model_tools() and
        verify_model_image_input() assign the api key with a trailing comma, so that
        openai.api_key is a tuple, and the requests are not authenticated.
        """
        model_checks.verify_model_streaming(provider_model=self.model)
        self.assertEqual(self.openai.api_key, API_KEY)

    @unittest.expectedFailure
    def test_summarization(self):
        """
        Test that a summary of 10 words or less succeeds.

        Expected to fail: verify_model_summarization() asks for a summary in 10 words or
        less, but checks that the summary is at most 10 characters long.
        """
        self.openai.chat.completions.create.return_value = completion("A short summary of seven words here.")
        self.assertTrue(model_checks.verify_model_summarization(provider_model=self.model))

    def test_verify_provider_model(self):
        """Test that a model that passes its checks is activated, and one that fails is deactivated."""
        self.model.supports_summarization = False
        self.model.supports_tools = True
        self.model.save()
        model_checks.verify_provider_model(self.model.id)
        self.assertTrue(ProviderModel.objects.get(pk=self.model.pk).is_active)

        self.reset()
        self.model.supports_search = True
        self.model.save()
        model_checks.verify_provider_model(self.model.id)
        self.assertFalse(ProviderModel.objects.get(pk=self.model.pk).is_active)
        self.assertIsNone(model_checks.verify_provider_model(999999999))


class TestVerificationSignals(ProviderTestBase):
    """Test that recording a verification's result, which sends a signal, works."""

    @unittest.expectedFailure
    def test_set_provider_verification(self):
        """
        Expected to fail: set_provider_verification() sends provider_verification_success and.

        provider_verification_failure with provider_verification= only, and their receivers
        then read provider.name, of provider=None, which raises AttributeError, so every
        Provider check raises.
        """
        from smarter.apps.provider.models import (
            ProviderVerificationTypes,  # pylint: disable=import-outside-toplevel
        )
        from smarter.apps.provider.utils import (  # pylint: disable=import-outside-toplevel
            get_provider_verification_for_type,
            set_provider_verification,
        )

        verification = get_provider_verification_for_type(self.provider, ProviderVerificationTypes.LOGO)
        set_provider_verification(provider_verification=verification, is_successful=False)
        set_provider_verification(provider_verification=verification, is_successful=True)
        self.assertTrue(ProviderVerification.objects.get(pk=verification.pk).is_successful)

    @unittest.expectedFailure
    def test_set_model_verification_success(self):
        """
        Expected to fail: set_model_verification() sends model_verification_success with.

        provider_model_verification= only, and handle_model_verification_success() then reads
        provider_model.name, of provider_model=None, which raises AttributeError, so every
        ProviderModel check that succeeds raises.
        """
        from smarter.apps.provider.models import (  # pylint: disable=import-outside-toplevel
            ProviderModelVerificationTypes,
        )
        from smarter.apps.provider.utils import (  # pylint: disable=import-outside-toplevel
            get_model_verification_for_type,
            set_model_verification,
        )

        model = ProviderModel.objects.create(provider=self.provider, name="test-signals-model")
        verification = get_model_verification_for_type(model, ProviderModelVerificationTypes.TOOLS)
        set_model_verification(provider_model_verification=verification, is_successful=False)
        set_model_verification(provider_model_verification=verification, is_successful=True)
        self.assertTrue(ProviderModelVerification.objects.get(pk=verification.pk).is_successful)
