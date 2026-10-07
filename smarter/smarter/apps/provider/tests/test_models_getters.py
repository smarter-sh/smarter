"""Test the module-level Provider getters in :mod:`smarter.apps.provider.models`, and the verification models' validity."""

import os
from datetime import timedelta
from unittest.mock import patch

from django.utils import timezone

from smarter.apps.account.models import Account
from smarter.apps.provider.models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderModelVerificationTypes,
    ProviderVerification,
    ProviderVerificationTypes,
    get_model_for_provider,
    get_models_for_provider,
    get_provider,
    get_providers,
)
from smarter.common.exceptions import SmarterBusinessRuleViolation, SmarterValueError

from .test_models import ProviderTestBase


class TestProviderGetters(ProviderTestBase):
    """Test get_provider(), get_providers(), get_model_for_provider() and get_models_for_provider()."""

    def setUp(self):
        super().setUp()
        # get_provider() and friends cache their results by name, so each test needs its own provider.
        self.provider = self.new_provider(f"test_provider_getters_{self._testMethodName}")
        Provider.objects.filter(pk=self.provider.pk).update(is_active=True)
        self.provider.refresh_from_db()
        self.name = self.provider.name
        patcher = patch.dict(os.environ, {f"{self.name.upper()}_API_KEY": "test-api-key"})
        patcher.start()
        self.addCleanup(patcher.stop)

    def new_model(self, name: str, **kwargs) -> ProviderModel:
        model = ProviderModel.objects.create(provider=self.provider, name=name, **kwargs)
        self.addCleanup(ProviderModel.objects.filter(pk=model.pk).delete)
        return model

    def test_get_provider(self):
        """An active provider is returned by name."""
        self.assertEqual(get_provider(provider_name=self.name).pk, self.provider.pk)

    def test_get_provider_that_does_not_exist(self):
        """An unknown provider name raises SmarterValueError."""
        with self.assertRaises(SmarterValueError):
            get_provider(provider_name=f"no_such_provider_{self.hash_suffix}")

    def test_get_inactive_provider(self):
        """An inactive provider raises SmarterBusinessRuleViolation."""
        provider = self.new_provider("test_provider_getters_inactive_provider")
        with self.assertRaises(SmarterBusinessRuleViolation):
            get_provider(provider_name=provider.name)

    def test_get_provider_of_an_inactive_account(self):
        """A provider whose account is inactive raises SmarterBusinessRuleViolation."""
        Account.objects.filter(pk=self.account.pk).update(is_active=False)
        self.addCleanup(Account.objects.filter(pk=self.account.pk).update, is_active=True)
        with self.assertRaises(SmarterBusinessRuleViolation):
            get_provider(provider_name=f"{self.name}")

    def test_get_providers(self):
        """Get_providers() includes the active provider."""
        self.assertIn(self.provider.pk, [provider.pk for provider in get_providers()])

    def test_get_default_and_named_model(self):
        """The default model, or a named one, is returned with the provider's api key."""
        self.new_model("default-model", is_default=True, is_active=True)
        self.new_model("named-model", is_active=True)
        default = get_model_for_provider(provider_name=self.name)
        self.assertEqual(default["model"], "default-model")
        self.assertEqual(default["api_key"], "test-api-key")
        self.assertEqual(default["provider_id"], self.provider.pk)
        named = get_model_for_provider(provider_name=self.name, model_name="named-model")
        self.assertEqual(named["model"], "named-model")
        models = get_models_for_provider(provider_name=self.name)
        self.assertEqual({model["model"] for model in models}, {"default-model", "named-model"})

    def test_get_model_that_does_not_exist(self):
        """An unknown model name raises SmarterValueError."""
        with self.assertRaises(SmarterValueError):
            get_model_for_provider(provider_name=self.name, model_name="no-such-model")

    def test_get_default_model_that_does_not_exist(self):
        """A provider without a default model raises SmarterValueError."""
        with self.assertRaises(SmarterValueError):
            get_model_for_provider(provider_name=self.name)

    def test_get_inactive_model(self):
        """An inactive model raises SmarterBusinessRuleViolation."""
        self.new_model("inactive-model", is_active=False)
        with self.assertRaises(SmarterBusinessRuleViolation):
            get_model_for_provider(provider_name=self.name, model_name="inactive-model")

    def test_get_model_for_a_provider_that_became_inactive(self):
        """Get_model_for_provider() rechecks that the provider is active."""
        self.new_model("default-model", is_default=True, is_active=True)
        provider = Provider.objects.get(pk=self.provider.pk)
        provider.is_active = False
        with patch("smarter.apps.provider.models.get_provider", return_value=provider):
            with self.assertRaises(SmarterBusinessRuleViolation):
                get_model_for_provider(provider_name=f"{self.name}_inactive")


class TestVerificationValidity(ProviderTestBase):
    """Test the verification models' is_valid and next_verification."""

    def backdate(self, verification):
        """
        Move updated_at a minute into the past.

        is_valid treats an elapsed time of 0 seconds as "never updated", so a
        verification saved within the last second is not yet valid.
        """
        type(verification).objects.filter(pk=verification.pk).update(updated_at=timezone.now() - timedelta(minutes=1))
        verification.refresh_from_db()
        return verification

    def test_provider_verification(self):
        """A fresh, successful provider verification is valid."""
        verification = ProviderVerification.objects.create(
            provider=self.provider, verification_type=ProviderVerificationTypes.API_CONNECTIVITY, is_successful=True
        )
        verification = self.backdate(verification)
        self.assertTrue(verification.is_valid)
        self.assertGreater(verification.next_verification, verification.updated_at)
        self.assertIn(self.provider.name, str(verification))

    def test_provider_model_verification(self):
        """A fresh, successful model verification is valid, and an unsaved one is not."""
        model = ProviderModel.objects.create(provider=self.provider, name="test-verified-model")
        self.addCleanup(ProviderModel.objects.filter(pk=model.pk).delete)
        verification = ProviderModelVerification.objects.create(
            provider_model=model, verification_type=ProviderModelVerificationTypes.TOOLS, is_successful=True
        )
        verification = self.backdate(verification)
        self.assertTrue(verification.is_valid)
        self.assertGreater(verification.next_verification, verification.updated_at)
        unsaved = ProviderModelVerification(
            provider_model=model, verification_type=ProviderModelVerificationTypes.TOOLS
        )
        self.assertFalse(unsaved.is_valid)
