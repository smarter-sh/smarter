"""Test Api v1 CLI commands for account"""

from .apiv1cli_base import ApiV1CliTestBase


class TestApiCliV1Account(ApiV1CliTestBase):
    """
    Test Api v1 CLI commands for account

    This class is a subclass of ApiV1CliTestBase, which is a subclass of
    ApiV1TestBase. ApiV1TestBase gives us access to the setUpClass and
    tearDownClass methods, which are used to uniformly create and delete
    a user, account, user_profile and token record for testing purposes.
    ApiV1CliTestBase gives us access to the abstract methods that we need
    to implement in order to test the Api v1 CLI commands for Account.

    """

    def test_apply(self) -> None:
        """Test apply command"""

    def test_describe(self) -> None:
        """Test describe command"""

    def test_delete(self) -> None:
        """Test delete command"""

    def test_deploy(self) -> None:
        """Test deploy command"""

    def test_example_manifest(self) -> None:
        """Test example-manifest command"""

    def test_get(self) -> None:
        """Test get command"""

    def test_logs(self) -> None:
        """Test logs command"""

    def test_undeploy(self) -> None:
        """Test undeploy command"""
