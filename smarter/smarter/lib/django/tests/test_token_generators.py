"""Test the SmarterValidator class."""

from unittest.mock import MagicMock, patch

from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from smarter.lib.django.token_generators import (
    ExpiringTokenGenerator,
    TokenConversionError,
    TokenExpiredError,
    TokenIntegrityError,
    TokenParseError,
)
from smarter.lib.unittest.base_classes import SmarterTestBase


class TestExpiringTokenGenerator(SmarterTestBase):
    """Test the ExpiringTokenGenerator class."""

    def setUp(self):
        self.token_gen = ExpiringTokenGenerator(expiration=100)
        self.user = MagicMock()
        self.user.pk = 123

    @patch("smarter.lib.django.token_generators.force_bytes")
    @patch("smarter.lib.django.token_generators.urlsafe_base64_encode")
    def test_user_to_uidb64(self, mock_encode, mock_force_bytes):
        mock_force_bytes.return_value = b"123"
        mock_encode.return_value = "abc"
        result = self.token_gen.user_to_uidb64(self.user)
        mock_force_bytes.assert_called_with(self.user.pk)
        self.assertEqual(result, "abc")

    @patch("smarter.lib.django.token_generators.User")
    @patch("smarter.lib.django.token_generators.urlsafe_base64_decode")
    def test_uidb64_to_user(self, mock_decode, mock_User):
        mock_decode.return_value = b"123"
        mock_User.objects.get.return_value = self.user
        result = self.token_gen.uidb64_to_user("abc")
        mock_User.objects.get.assert_called_with(pk=b"123")
        self.assertEqual(result, self.user)

    @patch("smarter.lib.django.token_generators.get_current_site")
    @patch("smarter.lib.django.token_generators.reverse")
    @patch.object(ExpiringTokenGenerator, "make_token")
    @patch.object(ExpiringTokenGenerator, "user_to_uidb64")
    def test_encode_link(self, mock_uidb64, mock_make_token, mock_reverse, mock_get_current_site):
        request = MagicMock()
        request.is_secure.return_value = True
        mock_get_current_site.return_value.domain = "example.com"
        mock_make_token.return_value = "tok"
        mock_uidb64.return_value = "uid"
        mock_reverse.return_value = "/reset/uid/tok/"
        url = self.token_gen.encode_link(request, self.user, "reset_link")
        self.assertTrue(url.startswith("https://example.com"))
        self.assertIn("tok", url)

    @patch.object(ExpiringTokenGenerator, "uidb64_to_user")
    @patch.object(ExpiringTokenGenerator, "validate")
    def test_decode_link(self, mock_validate, mock_uidb64_to_user):
        mock_uidb64_to_user.return_value = self.user
        result = self.token_gen.decode_link("uidb64", "token")
        mock_validate.assert_called_with(self.user, "token")
        self.assertEqual(result, self.user)

    @patch("smarter.lib.django.token_generators.User")
    @patch("smarter.lib.django.token_generators.urlsafe_base64_decode")
    def test_parse_link(self, mock_decode, mock_User):
        url = "https://example.com/reset/uidb64/token"
        mock_decode.return_value = b"123"
        mock_User.objects.get.return_value = self.user
        user, token = self.token_gen.parse_link(url)
        self.assertEqual(user, self.user)
        self.assertEqual(token, "token")

    @patch("smarter.lib.django.token_generators.timezone_now")
    def test_get_timestamp(self, mock_now):
        mock_now.return_value.timestamp.return_value = 1234567890
        self.assertEqual(self.token_gen.get_timestamp(), 1234567890)

    def test_adjusted_timestamp(self):
        ts = 100
        self.assertEqual(self.token_gen.adjusted_timestamp(ts), 100 + 2082844800)

    @patch.object(ExpiringTokenGenerator, "check_token")
    @patch.object(ExpiringTokenGenerator, "get_timestamp")
    def test_validate_success(self, mock_get_timestamp, mock_check_token):
        mock_check_token.return_value = True
        mock_get_timestamp.return_value = 2082844900
        token = "2s-abcdef"  # 2s in base36 is 100
        # adjusted_timestamp = 2082844800 + 100 = 2082844900
        # current_time - adjusted_timestamp = 0 <= expiration
        self.assertTrue(self.token_gen.validate(self.user, token))

    @patch.object(ExpiringTokenGenerator, "check_token")
    def test_validate_integrity_error(self, mock_check_token):
        mock_check_token.return_value = False
        with self.assertRaises(TokenIntegrityError):
            self.token_gen.validate(self.user, "badtoken")

    @patch.object(ExpiringTokenGenerator, "check_token")
    def test_validate_parse_error(self, mock_check_token):
        mock_check_token.return_value = True
        with self.assertRaises(TokenParseError):
            self.token_gen.validate(self.user, "bad-token-without-dash")

    @patch.object(ExpiringTokenGenerator, "check_token")
    def test_validate_conversion_error(self, mock_check_token):
        mock_check_token.return_value = True
        # base36_to_int will fail for non-base36
        with self.assertRaises(TokenConversionError):
            self.token_gen.validate(self.user, "bad!-abcdef")

    @patch.object(ExpiringTokenGenerator, "check_token")
    @patch.object(ExpiringTokenGenerator, "get_timestamp")
    def test_validate_expired(self, mock_get_timestamp, mock_check_token):
        mock_check_token.return_value = True
        mock_get_timestamp.return_value = 2082845001
        # token timestamp = 100, adjusted = 2082844900, now = 2082845001, diff = 101 > expiration=100
        token = "2s-abcdef"
        with self.assertRaises(TokenExpiredError):
            self.token_gen.validate(self.user, token)

    def test_user_to_uidb64_real(self):
        # This test uses the real urlsafe_base64_encode function

        user = MagicMock()
        user.pk = 42
        token_gen = ExpiringTokenGenerator()
        expected = urlsafe_base64_encode(force_bytes(user.pk))
        result = token_gen.user_to_uidb64(user)
        self.assertEqual(result, expected)
