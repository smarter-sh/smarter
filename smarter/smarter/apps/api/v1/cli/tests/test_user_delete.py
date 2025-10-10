"""Test Api v1 CLI commands for User"""

import logging
from http import HTTPStatus
from urllib.parse import urlencode

from django.urls import reverse

from smarter.apps.account.models import User
from smarter.apps.account.tests.factories import mortal_user_factory
from smarter.apps.api.v1.cli.urls import ApiV1CliReverseViews
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.conf import settings as smarter_settings
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.enum import SAMKeys

from .base_class import ApiV1CliTestBase


KIND = SAMKinds.USER.value


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.API_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        and level >= smarter_settings.log_level
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class TestApiCliV1UserDelete(ApiV1CliTestBase):
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

    def test_delete(self) -> None:
        """Test delete command."""
        test_user, _, test_user_profile = mortal_user_factory(account=self.account)
        username = test_user.username
        self.query_params = urlencode({"username": username})

        # ensure that the user exists before we delete it
        user = User.objects.get(username=username)
        self.assertIsInstance(user, User)

        path = reverse(self.namespace + ApiV1CliReverseViews.delete, kwargs=self.kwargs)
        url_with_query_params = f"{path}?{self.query_params}"
        response, status = self.get_response(path=url_with_query_params)
        logger.info("response: %s", response)

        # validate the response and status are both good
        self.assertEqual(status, HTTPStatus.OK)
        self.assertIsInstance(response, dict)

        try:
            confirmed_test_user = User.objects.get(username=username)
            self.fail(f"user {username} record was not deleted {confirmed_test_user}")
        except User.DoesNotExist:
            pass
