"""Test Api v1 CLI commands for account"""

from http import HTTPStatus

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase


class TestApiCliV1Account(ApiV1TestBase):
    """
    Test Api v1 CLI commands for account

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    Account.
    """

    def test_example_manifest(self) -> None:
        """Test example-manifest command"""

        kwargs = {"kind": "account"}
        path = reverse(ApiV1CliReverseViews.example_manifest, kwargs=kwargs)
        response, status = self.get_response(path)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        # validate the structure of the response
        print(response)

    def test_apply(self) -> None:
        """Test apply command"""
        pass

    def test_describe(self) -> None:
        """Test describe command"""
        pass

    def test_get(self) -> None:
        """Test get command"""
        pass

    def test_deploy(self) -> None:
        """Test deploy command"""
        pass

    def test_undeploy(self) -> None:
        """Test undeploy command"""
        pass

    def test_logs(self) -> None:
        """Test logs command"""
        pass

    def test_delete(self) -> None:
        """Test delete command"""
        pass
