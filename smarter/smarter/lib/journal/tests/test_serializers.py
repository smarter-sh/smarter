"""Test :mod:`smarter.lib.journal.serializers`."""

from http import HTTPStatus

from smarter.lib.journal.contract.models import SAMJournalApiOrmModel
from smarter.lib.journal.enum import SmarterJournalCliCommands, SmarterJournalThings
from smarter.lib.journal.models import SAMJournal
from smarter.lib.journal.serializers import (
    SAMJournalMiniSerializer,
    SAMJournalSerializer,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSAMJournalSerializers(SmarterTestBase):
    """Test the journal's serializers, for an anonymous request's entry."""

    def setUp(self):
        super().setUp()
        self.journal = SAMJournal.objects.create(
            thing=SmarterJournalThings.LLM_CLIENT.value,
            command=SmarterJournalCliCommands.PROMPT.value,
            request={"url": "http://localhost:9357/"},
            response={"data": "a completion"},
            status_code=HTTPStatus.CREATED,
        )
        self.addCleanup(self.journal.delete)

    def test_serializer(self):
        data = SAMJournalSerializer(self.journal).data
        self.assertEqual(
            set(data), {"key", "createdAt", "user", "thing", "command", "request", "response", "statusCode"}
        )
        self.assertIsNone(data["user"])
        self.assertEqual(data["command"], "prompt")
        self.assertEqual(data["statusCode"], 201)
        self.assertEqual(data["response"], {"data": "a completion"})

    def test_serializer_matches_the_contract(self):
        """Test that the serializer has the contract's fields, in camelCase."""
        data = SAMJournalSerializer(self.journal).data
        contract = SAMJournalApiOrmModel.from_model(self.journal).model_dump(mode="json")
        self.assertEqual(data["key"], contract["key"])
        self.assertEqual(data["statusCode"], contract["status_code"])
        self.assertEqual(data["request"], contract["request"])

    def test_mini_serializer(self):
        data = SAMJournalMiniSerializer(self.journal).data
        self.assertEqual(set(data), {"key", "createdAt", "user", "thing", "command", "statusCode"})
