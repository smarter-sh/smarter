"""Unit test base classes for Smarter."""

import copy
import importlib
from typing import Optional
from unittest.mock import patch

from django.test import RequestFactory

from smarter.apps.guardrail.manifest.brokers.guardrail import SAMGuardrailBroker
from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.serializers import GuardrailSerializer
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS
from smarter.apps.llmclient.models import LLMClient, LLMClientGuardrails
from smarter.lib import logging
from smarter.lib.manifest.broker import SAMBrokerErrorNotImplemented

from ..serializers import (
    AccountMiniSerializer,
    AccountSerializer,
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
    user_can_delete,
)
from .mixins import TestAccountMixin

logger = logging.getLogger(__name__)

SERIALIZER_MODULES = [
    "smarter.apps.connection.serializers",
    "smarter.apps.guardrail.serializers",
    "smarter.apps.llmclient.serializers",
    "smarter.apps.llmhost.serializers",
    "smarter.apps.mcpclient.serializers",
    "smarter.apps.orchestrator.serializers",
    "smarter.apps.llmtool.serializers",
    "smarter.apps.provider.serializers",
    "smarter.apps.proxy.serializers",
    "smarter.apps.secret.serializers",
    "smarter.apps.vectorsearch.serializers",
    "smarter.apps.vectorstore.serializers",
    "smarter.lib.drf.serializers.authtoken",
]


class TestSerializers(TestAccountMixin):
    """Test serializers for the account app."""

    test_serializers_logger_prefix = f"{logging.formatted_text(__name__)}.TestSerializers()"

    def test_account_serializer(self):
        """Test the AccountSerializer."""
        serializer = AccountSerializer(self.account)
        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_account_mini_serializer(self):
        """Test the AccountMiniSerializer."""
        serializer = AccountMiniSerializer(self.account)
        data = serializer.data
        self.assertIsInstance(data, dict)

    def test_user_profile_serializer(self):
        """Test the UserProfileSerializer."""
        serializer = UserProfileSerializer(self.user_profile)
        data = serializer.data
        self.assertIsInstance(data, dict)


class TestCanDelete(TestAccountMixin):
    """Test MetaDataWithOwnershipModelSerializer.can_delete, with the GuardrailSerializer."""

    def setUp(self):
        super().setUp()
        self.guardrail = Guardrail.objects.create(
            name="test_serializers_can_delete", user_profile=self.user_profile, **copy.deepcopy(GUARDRAIL_DEFAULTS)
        )
        self.addCleanup(Guardrail.objects.filter(pk=self.guardrail.pk).delete)

    def can_delete(self, user) -> Optional[bool]:
        """Return the serialized canDelete of the Guardrail, for a request by ``user``."""
        request = RequestFactory().get("/")
        request.user = user
        return GuardrailSerializer(self.guardrail, context={"request": request}).data["canDelete"]

    def test_can_delete(self):
        """Test that an owner may delete a Guardrail that no LLMClient uses."""
        self.assertIs(self.can_delete(self.admin_user), True)

    def test_cannot_delete_with_dependencies(self):
        """Test that an owner may not delete a Guardrail that an LLMClient uses."""
        llmclient = LLMClient.objects.create(name="test_serializers_can_delete", user_profile=self.user_profile)
        self.addCleanup(llmclient.delete)
        LLMClientGuardrails.objects.create(llmclient=llmclient, guardrail=self.guardrail)
        self.assertIs(self.can_delete(self.admin_user), False)

    def test_cannot_delete_without_ownership(self):
        """Test that a user without ownership permission may not delete the Guardrail."""
        self.assertIs(self.can_delete(self.non_admin_user), False)

    def test_can_delete_without_request(self):
        """Test that canDelete is False when the serializer has no request."""
        self.assertIs(GuardrailSerializer(self.guardrail).data["canDelete"], False)

    def test_user_can_delete(self):
        """Test user_can_delete(), which the serializers and the api contract's models share."""
        self.assertIs(user_can_delete(self.guardrail, "Guardrail", self.admin_user), True)
        self.assertIs(user_can_delete(self.guardrail, "Guardrail", None), False)
        self.assertIs(user_can_delete(self.guardrail, "NotAKind", self.admin_user), False)
        self.assertIs(user_can_delete(self.guardrail, None, self.admin_user), False)

    def test_user_can_delete_with_owned_pks(self):
        """Test that user_can_delete() reads ownership from owned_pks, when a list's page gives it."""
        self.assertIs(
            user_can_delete(self.guardrail, "Guardrail", self.admin_user, owned_pks={self.guardrail.pk}), True
        )
        self.assertIs(user_can_delete(self.guardrail, "Guardrail", self.admin_user, owned_pks=set()), False)

    def test_page_asks_for_ownership_once(self):
        """Test that serializing a page asks once which rows the user owns, with the same canDelete as one row."""
        other = Guardrail.objects.create(
            name="test_serializers_can_delete_other",
            user_profile=self.non_admin_user_profile,
            **copy.deepcopy(GUARDRAIL_DEFAULTS),
        )
        self.addCleanup(Guardrail.objects.filter(pk=other.pk).delete)
        request = RequestFactory().get("/")
        request.user = self.non_admin_user
        with (
            patch("smarter.apps.account.serializers.user_can_delete", wraps=user_can_delete) as can_delete,
            patch.object(
                Guardrail.objects,
                "with_ownership_permission_for",
                wraps=Guardrail.objects.with_ownership_permission_for,
            ) as ownership,
        ):
            data = GuardrailSerializer([self.guardrail, other], many=True, context={"request": request}).data
        self.assertEqual(ownership.call_count, 1)
        self.assertEqual(can_delete.call_count, 2)
        for row, item in zip((self.guardrail, other), data):
            single = GuardrailSerializer(row, context={"request": request}).data["canDelete"]
            self.assertEqual(item["canDelete"], single, row.name)

    def test_user_can_delete_builds_no_broker(self):
        """Test that user_can_delete() asks the broker class, so that a list page builds no broker per row."""
        with patch.object(SAMGuardrailBroker, "__init__", side_effect=AssertionError("a broker was built")):
            self.assertIs(user_can_delete(self.guardrail, "Guardrail", self.admin_user), True)

    def test_user_can_delete_when_dependents_fail(self):
        """Test that a resource whose dependents cannot be checked may not be deleted."""
        with patch.object(SAMGuardrailBroker, "has_dependents", side_effect=SAMBrokerErrorNotImplemented("no")):
            self.assertIs(user_can_delete(self.guardrail, "Guardrail", self.admin_user), False)

    def test_every_subclass_has_can_delete(self):
        """Test that every subclass of MetaDataWithOwnershipModelSerializer serializes can_delete."""
        for module in SERIALIZER_MODULES:
            importlib.import_module(module)
        subclasses, pending = [], list(MetaDataWithOwnershipModelSerializer.__subclasses__())
        while pending:
            subclass = pending.pop()
            subclasses.append(subclass)
            pending.extend(subclass.__subclasses__())
        self.assertGreater(len(subclasses), 10)
        for subclass in subclasses:
            with self.subTest(serializer=subclass.__name__):
                self.assertIn("can_delete", subclass().fields)
