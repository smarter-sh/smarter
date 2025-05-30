"""
Base class for Api v1 CLI tests.
"""

from smarter.apps.api.v1.tests.base_class import ApiV1TestBase


class ApiV1CliTestBase(ApiV1TestBase):
    """
    Abstract base class for Api v1 CLI tests.
    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    User.
    """
