# -*- coding: utf-8 -*-
# pylint: disable=wrong-import-position
"""Test API end points."""

# python stuff
import hashlib
import random
import unittest

from django.contrib.auth import get_user_model
from django.test import RequestFactory

# our stuff
from smarter.token_generators import ExpiringTokenGenerator


User = get_user_model()


class TestExpiringTokens(unittest.TestCase):
    """Test OpenAI Function Calling hook for refers_to."""

    def setUp(self):
        """Set up test fixtures."""
        username = "testuser" + hashlib.sha256(str(random.getrandbits(256)).encode("utf-8")).hexdigest()

        self.user = User.objects.create_user(username=username, password="12345")

    def tearDown(self):
        """Clean up test fixtures."""
        self.user.delete()

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
