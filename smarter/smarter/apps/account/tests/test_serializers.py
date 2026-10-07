"""Unit test base classes for Smarter."""

import copy
import importlib
from typing import Optional

from django.test import RequestFactory

from smarter.apps.guardrail.models import Guardrail
from smarter.apps.guardrail.serializers import GuardrailSerializer
from smarter.apps.guardrail.tests.base_classes import GUARDRAIL_DEFAULTS
from smarter.apps.llmclient.models import LLMClient, LLMClientGuardrails
from smarter.lib import logging

from ..serializers import (
    AccountMiniSerializer,
    AccountSerializer,
    MetaDataWithOwnershipModelSerializer,
    UserProfileSerializer,
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
    "smarter.apps.plugin.serializers",
    "smarter.apps.provider.serializers",
    "smarter.apps.proxy.serializers",
    "smarter.apps.secret.serializers",
    "smarter.apps.vectorsearch.serializers",
    "smarter.apps.vectorstore.serializers",
    "smarter.lib.drf.serializers.authtoken",
]


class TestSerializers(TestAccountMixin):
    """Test serializers for the account app."""

    test_serializers_logger_prefix = logging.formatted_text(f"{__name__}.TestSerializers()")

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
