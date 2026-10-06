"""Test :mod:`smarter.apps.provider.services.text_completion.validators`."""

from unittest import TestCase

from smarter.apps.provider.services.text_completion import validators
from smarter.common.exceptions import SmarterValueError

MESSAGES = [{"role": "user", "content": "hi"}]


class TestValidators(TestCase):
    """Test that each validator accepts valid input and refuses invalid input."""

    def test_validate_temperature(self):
        validators.validate_temperature(0.5)
        with self.assertRaises(SmarterValueError):
            validators.validate_temperature(2)

    def test_validate_max_completion_tokens(self):
        validators.validate_max_completion_tokens(100)
        with self.assertRaises(TypeError):
            validators.validate_max_completion_tokens("100")
        with self.assertRaises(SmarterValueError):
            validators.validate_max_completion_tokens(0)

    def test_validate_endpoint_and_object_type(self):
        for validator in (validators.validate_endpoint, validators.validate_object_types):
            with self.subTest(validator=validator.__name__):
                with self.assertRaises(TypeError):
                    validator(1)
                with self.assertRaises(SmarterValueError):
                    validator("not-a-valid-value")

    def test_validate_request_body(self):
        with self.assertRaises(TypeError):
            validators.validate_request_body([])

    def test_validate_messages(self):
        validators.validate_messages({"messages": MESSAGES})
        for request in (
            {},
            {"messages": "x"},
            {"messages": ["x"]},
            {"messages": [{"content": "hi"}]},
            {"messages": [{"role": "nobody", "content": "hi"}]},
            {"messages": [{"role": "user"}]},
        ):
            with self.subTest(request=request), self.assertRaises(SmarterValueError):
                validators.validate_messages(request)

    def test_validate_completion_request(self):
        validators.validate_completion_request(
            {"messages": MESSAGES, "model": "m", "temperature": 0.5, "max_completion_tokens": 10}
        )
        validators.validate_completion_request({"messages": MESSAGES}, version="v0")
        for missing in ("model", "temperature", "max_completion_tokens"):
            request = {"messages": MESSAGES, "model": "m", "temperature": 0.5, "max_completion_tokens": 10}
            request.pop(missing)
            with self.subTest(missing=missing), self.assertRaises(SmarterValueError):
                validators.validate_completion_request(request)

    def test_validate_embedding_request(self):
        validators.validate_embedding_request({"input_text": "hi"})
        with self.assertRaises(SmarterValueError):
            validators.validate_embedding_request({})
