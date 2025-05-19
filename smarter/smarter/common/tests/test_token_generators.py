# pylint: disable=wrong-import-position
"""Test API end points."""

from django.test import RequestFactory

# our stuff
from smarter.apps.account.tests.mixins import TestAccountMixin

from ...lib.django.token_generators import ExpiringTokenGenerator


class TestExpiringTokens(TestAccountMixin):
    """Test url token generators."""

    def test_token(self):
        """test that we can encode and decode an expiring link."""
        expiring_token = ExpiringTokenGenerator()
        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.admin_user

        # basic token encode/decode test
        token = expiring_token.make_token(user=self.admin_user)
        self.assertTrue(expiring_token.check_token(user=self.admin_user, token=token))
        expiring_token.validate(user=self.admin_user, token=token)

        # create an encoded link for a url pattern that expects a uidb64 and token
        encoded_link = expiring_token.encode_link(
            request=request, user=self.admin_user, reverse_link="password_reset_link"
        )
        decoded_user, _ = expiring_token.parse_link(url=encoded_link)
        self.assertEqual(decoded_user, self.admin_user)

        # create an encoded link for a url pattern that expects a uidb64 and token
        user_to_uidb64 = expiring_token.user_to_uidb64(self.admin_user)
        decoded_user = expiring_token.decode_link(user_to_uidb64, token)
        self.assertEqual(decoded_user, self.admin_user)
