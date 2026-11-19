"""Test smarter.lib.django.http.client_errors."""

from django.core.exceptions import ValidationError
from django.db import IntegrityError, OperationalError
from django.db.models import ProtectedError, RestrictedError
from rest_framework.exceptions import ParseError

from smarter.common.exceptions import (
    SmarterBusinessRuleViolation,
    SmarterConfigurationError,
    SmarterValueError,
)
from smarter.lib.django.http.client_errors import (
    CLIENT_ERROR_TYPES,
    INTEGRITY_ERROR_MESSAGE,
    PROTECTED_ERROR_MESSAGE,
    REQUEST_DATA_ERROR_TYPES,
    client_error_message,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

FALLBACK = "An error occurred while renaming the Secret."


class TestClientErrorMessage(SmarterTestBase):
    """Test which exceptions' messages reach the client, and which are replaced by the fallback."""

    def test_validation_error_gives_its_message(self):
        """A ValidationError is raised for the client, so its message is sent."""
        e = ValidationError("Name must be lower case.")
        self.assertEqual(client_error_message(e, FALLBACK), "Name must be lower case.")

    def test_validation_error_joins_its_messages(self):
        """A ValidationError of several fields, as full_clean() raises, gives all of its messages."""
        e = ValidationError({"name": ["Name is taken."], "version": ["Version is not valid."]})
        message = client_error_message(e, FALLBACK)
        self.assertIn("Name is taken.", message)
        self.assertIn("Version is not valid.", message)

    def test_smarter_value_error_gives_its_message_without_the_label(self):
        """A SmarterValueError gives its message, not the 'Smarter Value Error: ' that str() adds."""
        e = SmarterValueError("Version '1' is not a valid semantic version.")
        self.assertEqual(client_error_message(e, FALLBACK), "Version '1' is not a valid semantic version.")

    def test_business_rule_violation_gives_its_message(self):
        """A SmarterBusinessRuleViolation gives its message."""
        e = SmarterBusinessRuleViolation("The account has too many users.")
        self.assertEqual(client_error_message(e, FALLBACK), "The account has too many users.")

    def test_integrity_error_gives_a_fixed_message(self):
        """An IntegrityError names the schema, so the client gets a fixed message about the conflict."""
        e = IntegrityError(1062, "Duplicate entry 'x-5' for key 'unique_name_user_profile'")
        message = client_error_message(e, FALLBACK)
        self.assertEqual(message, INTEGRITY_ERROR_MESSAGE)
        self.assertNotIn("unique_name_user_profile", message)

    def test_protected_error_gives_a_fixed_message(self):
        """A ProtectedError or RestrictedError lists the rows that refer to the resource, so the client gets a fixed message."""
        for error_class in (ProtectedError, RestrictedError):
            with self.subTest(error=error_class.__name__):
                e = error_class("Cannot delete some instances of model 'Secret'", set())
                self.assertEqual(client_error_message(e, FALLBACK), PROTECTED_ERROR_MESSAGE)

    def test_other_database_error_gives_the_fallback(self):
        """A database error that the client didn't cause, e.g. a lost connection, gives the fallback."""
        e = OperationalError(2006, "MySQL server has gone away")
        self.assertEqual(client_error_message(e, FALLBACK), FALLBACK)
        self.assertNotIsInstance(e, CLIENT_ERROR_TYPES)

    def test_client_error_types(self):
        """The client's errors are a subset of the errors of the client's data, and neither includes a bug's exception."""
        for error_class in CLIENT_ERROR_TYPES:
            with self.subTest(error=error_class.__name__):
                self.assertIn(error_class, REQUEST_DATA_ERROR_TYPES)
        for data_error_class in (TypeError, ValueError, ParseError):
            with self.subTest(error=data_error_class.__name__):
                self.assertNotIn(data_error_class, CLIENT_ERROR_TYPES)
                self.assertIn(data_error_class, REQUEST_DATA_ERROR_TYPES)
        for bug_class in (KeyError, AttributeError, RuntimeError, OperationalError):
            with self.subTest(error=bug_class.__name__):
                self.assertFalse(issubclass(bug_class, REQUEST_DATA_ERROR_TYPES))

    def test_other_smarter_error_gives_the_fallback(self):
        """A Smarter error that isn't about the client's input, e.g. a configuration error, gives the fallback."""
        e = SmarterConfigurationError("SMARTER_SECRET_KEY is not set.")
        self.assertEqual(client_error_message(e, FALLBACK), FALLBACK)

    def test_other_exception_gives_the_fallback(self):
        """Any other exception gives the fallback."""
        e = KeyError("user_profile")
        self.assertEqual(client_error_message(e, FALLBACK), FALLBACK)
