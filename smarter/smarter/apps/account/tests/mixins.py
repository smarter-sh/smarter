"""Unit test class."""

import logging

from django.test import RequestFactory

from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.unittest.base_classes import SmarterTestBase

from .factories import admin_user_factory, factory_account_teardown, mortal_user_factory

logger = logging.getLogger(__name__)
HERE = __name__
logger_prefix = formatted_text(f"{HERE}.TestAccountMixin()")


class TestAccountMixin(SmarterTestBase):
    """A mixin that adds class-level account and user creation/destruction."""

    test_account_mixin_logger_prefix = formatted_text(f"{HERE}.TestAccountMixin()")

    @classmethod
    def setUpClass(cls):
        """
        Set up the test class with a single account, and admin and non-admin users.
        using the class setup so that we retain the same user_profile for each test,
        which is needed so that the django Secret model can be queried.
        """
        super().setUpClass()
        title = f" {logger_prefix}.setUpClass() "
        msg = "*" * ((cls.line_width - len(title)) // 2) + title + "*" * ((cls.line_width - len(title)) // 2)
        logger.debug(msg)
        cls.admin_user, cls.account, cls.user_profile = admin_user_factory()
        cls.non_admin_user, _, cls.non_admin_user_profile = mortal_user_factory(account=cls.account)

    @classmethod
    def tearDownClass(cls):
        title = f" {logger_prefix}.tearDownClass() "
        msg = "*" * ((cls.line_width - len(title)) // 2) + title + "*" * ((cls.line_width - len(title)) // 2)
        logger.debug(msg)
        try:
            factory_account_teardown(user=cls.admin_user, account=None, user_profile=cls.user_profile)
            factory_account_teardown(
                user=cls.non_admin_user, account=cls.account, user_profile=cls.non_admin_user_profile
            )
        # pylint: disable=W0718
        except Exception:
            pass
        finally:
            super().tearDownClass()

    def setUp(self):
        """We use different manifest test data depending on the test case."""
        super().setUp()
        self._manifest = None
        self._manifest_path = None
        self._loader = None
        self._model = None
        title = f" {logger_prefix}.{self._testMethodName}() "
        msg = "-" * ((self.line_width - len(title)) // 2) + title + "-" * ((self.line_width - len(title)) // 2)
        logger.debug(msg)

    def tearDown(self):
        """We use different manifest test data depending on the test case."""
        title = f" {logger_prefix}.tearDown() {self._testMethodName} "
        msg = "-" * ((self.line_width - len(title)) // 2) + title + "-" * ((self.line_width - len(title)) // 2)
        logger.debug(msg)
        self._manifest = None
        self._manifest_path = None
        self._loader = None
        self._model = None
        super().tearDown()

    @property
    def ready(self) -> bool:
        """Return True if the broker is ready."""
        if not super().ready:
            return False

        self.assertIsNotNone(self.account, "Account not initialized in ready() check.")
        self.assertIsNotNone(self.admin_user, "Admin user not initialized in ready() check.")
        self.assertIsNotNone(self.user_profile, "Admin user profile not initialized in ready() check.")
        self.assertIsNotNone(self.non_admin_user, "Non-admin user not initialized in ready() check.")
        self.assertIsNotNone(self.non_admin_user_profile, "Non-admin user profile not initialized in ready() check.")

        return True

    def request_factory(self) -> RequestFactory:
        """
        Prepare and get a response from an api/v1/ endpoint.
        """

        factory = RequestFactory()
        return factory
