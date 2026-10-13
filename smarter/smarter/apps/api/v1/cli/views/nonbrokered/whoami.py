# pylint: disable=W0613
"""Smarter API command-line interface 'whoami' view."""

from http import HTTPStatus

from smarter.apps.account.serializers import AccountSerializer, UserSerializer
from smarter.apps.api.v1.contract.models import CliApiWhoami
from smarter.common.conf import smarter_settings
from smarter.lib.journal.enum import (
    SmarterJournalApiResponseKeys,
    SmarterJournalCliCommands,
)
from smarter.lib.journal.http import SmarterJournaledJsonResponse

from ..base import APIV1CLIViewNotFoundError, CliBaseApiView


class ApiV1CliWhoamiApiView(CliBaseApiView):
    """
    Smarter API command-line interface 'whoami' view.

    An error, e.g. an api key's user without a user profile, is raised, and returned by
    :meth:`CliBaseApiView.dispatch` as a journaled error response.
    """

    @property
    def formatted_class_name(self) -> str:
        """Returns the class name in a formatted string along with the name of this mixin."""
        inherited_class = super().formatted_class_name
        this_class = f".{ApiV1CliWhoamiApiView.__name__}[{id(self)}]"
        return f"{inherited_class}{self.formatted_text(this_class)}"

    def whoami(self):
        """
        The api key's user and account, and the platform's environment.

        :returns: The journaled response.
        :rtype: SmarterJournaledJsonResponse
        :raises APIV1CLIViewNotFoundError: If the user has no user profile, which is a 404.
        """
        if not self.user_profile:
            raise APIV1CLIViewNotFoundError("User profile not found.")
        whoami = CliApiWhoami.model_validate(
            {
                "user": UserSerializer(self.user_profile.user).data,
                "account": AccountSerializer(self.user_profile.account).data,
                "environment": smarter_settings.environment,
            }
        )
        data = {SmarterJournalApiResponseKeys.DATA: whoami.model_dump(mode="json")}
        return SmarterJournaledJsonResponse(
            request=self.request,
            command=SmarterJournalCliCommands(SmarterJournalCliCommands.WHOAMI),
            data=data,
            status=HTTPStatus.OK.value,
        )

    def post(self, request):
        """ApiV1CliWhoamiApiView post view."""
        response = self.whoami()
        return response
