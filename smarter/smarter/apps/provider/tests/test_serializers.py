"""
Test the get_queryset() methods of the provider serializers, which filter by the request's ``name``, ``model_name`` and ``verification_type`` query parameters.

The provider lookups are mocked, so no provider has to exist.
"""

from types import SimpleNamespace
from unittest.mock import patch

from django.test import RequestFactory

from smarter.apps.provider.models import (
    Provider,
    ProviderModel,
    ProviderModelVerification,
    ProviderVerification,
)
from smarter.apps.provider.serializers import (
    ProviderModelSerializer,
    ProviderModelVerificationSerializer,
    ProviderSerializer,
    ProviderVerificationSerializer,
)
from smarter.common.exceptions import SmarterException
from smarter.lib.unittest.base_classes import SmarterTestBase

MODULE = "smarter.apps.provider.serializers"
MISSING_PK = -1


def make_serializer(serializer_class, **query):
    serializer = serializer_class()
    serializer.request = RequestFactory().get("/", data=query)
    return serializer


def where_pks(queryset) -> str:
    """The SQL WHERE clause of a queryset, for asserting what it filters on."""
    return str(queryset.query).split("WHERE", 1)[-1]


class TestProviderSerializerQuerysets(SmarterTestBase):
    """Test ProviderSerializer.get_queryset()."""

    def test_by_name(self):
        with patch(f"{MODULE}.get_provider", return_value=SimpleNamespace(pk=MISSING_PK)) as get_provider:
            queryset = make_serializer(ProviderSerializer, name="openai").get_queryset()
        get_provider.assert_called_once_with(provider_name="openai")
        self.assertEqual(queryset.model, Provider)
        self.assertIn(str(MISSING_PK), where_pks(queryset))
        self.assertFalse(queryset.exists())

    def test_all_providers(self):
        providers = [SimpleNamespace(pk=MISSING_PK), SimpleNamespace(pk=MISSING_PK - 1)]
        with patch(f"{MODULE}.get_providers", return_value=providers):
            queryset = make_serializer(ProviderSerializer).get_queryset()
        self.assertIn(str(MISSING_PK - 1), where_pks(queryset))
        self.assertFalse(queryset.exists())

    def test_all_providers_error(self):
        with patch(f"{MODULE}.get_providers", side_effect=SmarterException("no providers")):
            queryset = make_serializer(ProviderSerializer).get_queryset()
        self.assertEqual(list(queryset), [])


class TestProviderModelSerializerQuerysets(SmarterTestBase):
    """Test ProviderModelSerializer.get_queryset()."""

    def test_by_name_and_model_name(self):
        with patch(
            f"{MODULE}.get_model_for_provider", return_value=SimpleNamespace(pk=MISSING_PK)
        ) as get_model_for_provider:
            queryset = make_serializer(ProviderModelSerializer, name="openai", model_name="gpt").get_queryset()
        get_model_for_provider.assert_called_once_with(provider_name="openai", model_name="gpt")
        self.assertEqual(queryset.model, ProviderModel)
        self.assertIn(str(MISSING_PK), where_pks(queryset))

    def test_by_name_and_model_name_error(self):
        with patch(f"{MODULE}.get_model_for_provider", side_effect=SmarterException("no model")):
            queryset = make_serializer(ProviderModelSerializer, name="openai", model_name="gpt").get_queryset()
        self.assertEqual(list(queryset), [])

    def test_by_name(self):
        models = [SimpleNamespace(pk=MISSING_PK)]
        with patch(f"{MODULE}.get_models_for_provider", return_value=models) as get_models_for_provider:
            queryset = make_serializer(ProviderModelSerializer, name="openai").get_queryset()
        get_models_for_provider.assert_called_once_with(provider_name="openai")
        self.assertIn(str(MISSING_PK), where_pks(queryset))

    def test_by_name_error(self):
        with patch(f"{MODULE}.get_models_for_provider", side_effect=SmarterException("no provider")):
            queryset = make_serializer(ProviderModelSerializer, name="openai").get_queryset()
        self.assertEqual(list(queryset), [])

    def test_active_models(self):
        queryset = make_serializer(ProviderModelSerializer).get_queryset()
        self.assertIn("is_active", where_pks(queryset))
        self.assertTrue(all(model.is_active for model in queryset[:5]))


class TestProviderVerificationSerializerQuerysets(SmarterTestBase):
    """Test ProviderVerificationSerializer.get_queryset()."""

    def test_by_name_and_verification_type(self):
        with patch(f"{MODULE}.get_provider", return_value=Provider(pk=MISSING_PK)):
            queryset = make_serializer(
                ProviderVerificationSerializer, name="openai", verification_type="api_connectivity"
            ).get_queryset()
        self.assertEqual(queryset.model, ProviderVerification)
        self.assertIn("verification_type", where_pks(queryset))
        self.assertFalse(queryset.exists())

    def test_by_name(self):
        with patch(f"{MODULE}.get_provider", return_value=Provider(pk=MISSING_PK)):
            queryset = make_serializer(ProviderVerificationSerializer, name="openai").get_queryset()
        self.assertNotIn("verification_type", where_pks(queryset))
        self.assertFalse(queryset.exists())

    def test_by_name_error(self):
        with patch(f"{MODULE}.get_provider", side_effect=SmarterException("no provider")):
            queryset = make_serializer(ProviderVerificationSerializer, name="openai").get_queryset()
        self.assertEqual(list(queryset), [])


class TestProviderModelVerificationSerializerQuerysets(SmarterTestBase):
    """Test ProviderModelVerificationSerializer.get_queryset()."""

    def test_by_model_and_verification_type(self):
        with patch(f"{MODULE}.get_model_for_provider", return_value=ProviderModel(pk=MISSING_PK)):
            queryset = make_serializer(
                ProviderModelVerificationSerializer, name="openai", model_name="gpt", verification_type="streaming"
            ).get_queryset()
        self.assertEqual(queryset.model, ProviderModelVerification)
        self.assertIn("verification_type", where_pks(queryset))
        self.assertFalse(queryset.exists())

    def test_by_model(self):
        with patch(f"{MODULE}.get_model_for_provider", return_value=ProviderModel(pk=MISSING_PK)):
            queryset = make_serializer(
                ProviderModelVerificationSerializer, name="openai", model_name="gpt"
            ).get_queryset()
        self.assertNotIn("verification_type", where_pks(queryset))
        self.assertFalse(queryset.exists())

    def test_error(self):
        with patch(f"{MODULE}.get_model_for_provider", side_effect=SmarterException("no model")):
            queryset = make_serializer(ProviderModelVerificationSerializer, name="openai").get_queryset()
        self.assertEqual(list(queryset), [])
