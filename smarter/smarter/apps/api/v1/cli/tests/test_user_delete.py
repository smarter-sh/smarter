"""Test Api v1 CLI commands for User"""

from http import HTTPStatus
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.tests.base_class import ApiV1TestBase
from smarter.lib.django.user import User
from smarter.lib.manifest.enum import SAMKeys


KIND = SAMKinds.USER.value


class TestApiCliV1UserDelete(ApiV1TestBase):
    """
    Test Api v1 CLI commands for User

    This class is a subclass of ApiV1TestBase, which gives us access to the
    setUpClass and tearDownClass methods, which are used to uniformly
    create and delete a user, account, user_profile and token record for
    testing purposes. ApiV1CliTestBase gives us access to the abstract methods
    that we need to implement in order to test the Api v1 CLI commands for
    User.
    """

    def setUp(self):
        super().setUp()
        self.kwargs = {SAMKeys.KIND.value: KIND}
        self.query_params = urlencode({"username": self.user.username})

    def test_delete(self) -> None:
        """Test delete command."""
        username = self.user.username
        path = reverse(ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(url_with_query_params)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        try:
            User.objects.get(username=username)
            self.fail("Token record was not deleted")
        except User.DoesNotExist:
            pass
