"""Unit test class."""

# pylint: disable=W0104

import unittest

from .factories import (
    admin_user_factory,
    factory_account_teardown,
    generate_hash_suffix,
    mortal_user_factory,
)


class TestAccountMixin(unittest.TestCase):
    """A mixin that adds class-level account and user creation/destruction."""

    @classmethod
    def setUpClass(cls):
        """
        Set up the test class with a single account, and admin and non-admin users.
        using the class setup so that we retain the same user_profile for each test,
        which is needed so that the django Secret model can be queried.
        """
        cls.hash_suffix = generate_hash_suffix()
        cls.admin_user, cls.account, cls.user_profile = admin_user_factory()
        cls.non_admin_user, _, cls.non_admin_user_profile = mortal_user_factory(account=cls.account)

    @classmethod
    def tearDownClass(cls):
        factory_account_teardown(user=cls.admin_user, account=None, user_profile=cls.user_profile)
        factory_account_teardown(user=cls.non_admin_user, account=cls.account, user_profile=cls.non_admin_user_profile)

    def setUp(self):
        """We use different manifest test data depending on the test case."""
        self._manifest = None
        self._manifest_path = None
        self._loader = None
        self._model = None
