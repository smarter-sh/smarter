# pylint: disable=wrong-import-position
"""Test API end points."""

from django.test import RequestFactory

# our stuff
from smarter.apps.account.tests.factories import (
    admin_user_factory,
    factory_account_teardown,
)
from smarter.lib.unittest.base_classes import SmarterTestBase

from ...lib.django.token_generators import ExpiringTokenGenerator


class TestExpiringTokens(SmarterTestBase):
    """Test url token generators."""

    def setUp(self):
        """Set up test fixtures."""
        super().setUp()
        self.user, self.account, self.user_profile = admin_user_factory()

    def tearDown(self):
        """Clean up test fixtures."""
        factory_account_teardown(self.user, self.account, self.user_profile)
        super().tearDown()

    def test_token(self):
        """test that we can encode and decode an expiring link."""
        expiring_token = ExpiringTokenGenerator()
        rf = RequestFactory()
        request = rf.get("/")
        request.user = self.user

        # basic token encode/decode test
        token = expiring_token.make_token(user=self.user)
        self.assertTrue(expiring_token.check_token(user=self.user, token=token))
        expiring_token.validate(user=self.user, token=token)

        # create an encoded link for a url pattern that expects a uidb64 and token
        encoded_link = expiring_token.encode_link(request=request, user=self.user, reverse_link="password_reset_link")
        decoded_user, _ = expiring_token.parse_link(url=encoded_link)
        self.assertEqual(decoded_user, self.user)

        # create an encoded link for a url pattern that expects a uidb64 and token
        user_to_uidb64 = expiring_token.user_to_uidb64(self.user)
        decoded_user = expiring_token.decode_link(user_to_uidb64, token)
        self.assertEqual(decoded_user, self.user)
