"""Test :class:`smarter.lib.journal.enum.SmarterJournalCliCommands`, for the 'validate' command."""

from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.models import SAMJournal
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestSmarterJournalCliCommandsValidate(SmarterTestBase):
    """Test that 'validate' is a journaled cli command."""

    def test_value(self):
        self.assertEqual(SmarterJournalCliCommands.VALIDATE.value, "validate")
        self.assertIn("validate", SmarterJournalCliCommands.all())

    def test_choices(self):
        self.assertIn(("validate", "validate"), SmarterJournalCliCommands.choices())

    def test_past_tense(self):
        self.assertEqual(SmarterJournalCliCommands.past_tense()["validate"], "validated")

    def test_every_choice_has_a_past_tense(self):
        past_tense = SmarterJournalCliCommands.past_tense()
        for value, _ in SmarterJournalCliCommands.choices():
            self.assertIn(value, past_tense)

    def test_from_url(self):
        """Test that the cli api's validate url is journaled as the 'validate' command."""
        self.assertEqual(SmarterJournalCliCommands.from_url("http://localhost:9357/api/v1/cli/validate/"), "validate")

    def test_journal_model_choices(self):
        """Test that SAMJournal.command accepts 'validate', i.e. migration 0006 matches the enum."""
        choices = [value for value, _ in SAMJournal._meta.get_field("command").choices]
        self.assertIn("validate", choices)
