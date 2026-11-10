"""Unit test class."""

from datetime import datetime
from typing import Optional

from django.db import connection
from django.test import RequestFactory
from django.utils.crypto import get_random_string

from smarter.apps.account.models import Account, User, UserProfile
from smarter.apps.account.user_merge import (
    UNIQUE_EMAIL_INDEX,
    create_unique_email_index,
    drop_unique_email_index,
)
from smarter.lib import logging
from smarter.lib.unittest.base_classes import SmarterTestBase

from .factories import admin_user_factory, factory_account_teardown, mortal_user_factory

DUPLICATE_USERNAME_PREFIX = "test_duplicate_user_"
"""The username prefix of the users that :class:`DuplicateUsersMixin` creates, so that they can be cleaned up."""

logger = logging.getLogger(__name__)
HERE = __name__
logger_prefix = f"{logging.SmarterFormattedText.text(HERE)}.TestAccountMixin()"


class TestAccountMixin(SmarterTestBase):
    """A mixin that adds class-level account and user creation/destruction."""

    admin_user: User
    account: Account
    user_profile: UserProfile
    non_admin_user: User
    non_admin_user_profile: UserProfile

    test_account_mixin_logger_prefix = f"{logging.SmarterFormattedText.text(HERE)}.TestAccountMixin()"

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
        # Assign class-level user/account attributes to instance for reliable access
        self.admin_user = self.__class__.admin_user
        self.account = self.__class__.account
        self.user_profile = self.__class__.user_profile
        self.non_admin_user = self.__class__.non_admin_user
        self.non_admin_user_profile = self.__class__.non_admin_user_profile
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
        """Prepare and get a response from an api/v1/ endpoint."""

        factory = RequestFactory()
        return factory


class DuplicateUsersMixin(TestAccountMixin):
    """
    Create users who share an email address, which the unique index on ``auth_user.email`` forbids.

    The index is dropped for the test class, and created again afterwards. Every user that
    :meth:`duplicate_user` created, and that a merge didn't delete, is deleted after each test.
    """

    @staticmethod
    def unique_email_index_exists() -> bool:
        """Return True if ``auth_user`` has the unique index on email addresses."""
        with connection.cursor() as cursor:
            cursor.execute("SHOW INDEX FROM auth_user WHERE Key_name = %s", [UNIQUE_EMAIL_INDEX])
            rows = cursor.fetchall()
        return len(rows) > 0

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        if cls.unique_email_index_exists():
            with connection.schema_editor(atomic=False) as editor:
                drop_unique_email_index(editor)

    def tearDown(self):
        User.objects.filter(username__startswith=DUPLICATE_USERNAME_PREFIX).delete()
        super().tearDown()

    @classmethod
    def tearDownClass(cls):
        try:
            User.objects.filter(username__startswith=DUPLICATE_USERNAME_PREFIX).delete()
            if not cls.unique_email_index_exists():
                with connection.schema_editor(atomic=False) as editor:
                    create_unique_email_index(editor)
        finally:
            super().tearDownClass()

    def duplicate_user(
        self,
        email: str,
        last_login: Optional[datetime] = None,
        password: Optional[str] = None,
        account: Optional[Account] = None,
        with_profile: bool = True,
    ) -> User:
        """
        Create a user, and a profile in ``account``.

        :param email: The email address, which another user may already have.
        :param last_login: When the user last signed in, or ``None`` if they never did.
        :param password: The password, or ``None`` for an unusable one, as social sign-in leaves.
        :param account: The profile's account. Default: the test class's account.
        :param with_profile: Create the profile.
        :returns: The user.
        """
        username = f"{DUPLICATE_USERNAME_PREFIX}{get_random_string(10).lower()}"
        user = User.objects.create_user(username=username, email=email, password=password)
        if last_login is not None:
            user.last_login = last_login
            user.save(update_fields=["last_login"])
        if with_profile:
            profile_account = account or self.account
            UserProfile.objects.create(user=user, account=profile_account, is_test=True)
        return user
