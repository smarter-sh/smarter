"""Smarter API command-line interface Base class API view"""

import json
import logging
import re
from http import HTTPStatus
from typing import Type

import yaml
from django.core.handlers.wsgi import WSGIRequest
from django.http import QueryDict
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.manifests.version import SMARTER_API_VERSION
from smarter.common.exceptions import SmarterExceptionBase
from smarter.lib.django.request import SmarterRequestMixin
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonErrorResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    SAMBrokerReadOnlyError,
)
from smarter.lib.manifest.exceptions import SAMBadRequestError
from smarter.lib.manifest.loader import SAMLoader


logger = logging.getLogger(__name__)


class APIV1CLIViewError(SmarterExceptionBase):
    """Base class for all APIV1CLIView errors."""

    @property
    def get_formatted_err_message(self):
        return "Smarter api v1 command-line interface error"


# pylint: disable=too-many-instance-attributes
class CliBaseApiView(APIView, SmarterRequestMixin):
    """
    Smarter API command-line interface Base class API view. Handles
    common tasks for all /api/v1/cli views:
    - Authenticates the request using either knox TokenAuthentication
      or Django SessionAuthentication.
    - Initializes the SAMLoader and AbstractBroker instances.
    - Resolves the manifest kind and broker for the yaml manifest document.
    - Sets the user profile for the request.
    """

    authentication_classes = (SmarterTokenAuthentication,)
    permission_classes = (IsAuthenticated,)

    _BrokerClass: Type[AbstractBroker] = None
    _broker: AbstractBroker = None
    _loader: SAMLoader = None
    _manifest_data: json = None
    _manifest_kind: str = None
    _manifest_name: str = None
    _manifest_load_failed: bool = False
    _params: dict[str, any] = None
    _prompt: str = None

    def __init__(self, *args, **kwargs):
        APIView.__init__(self, *args, **kwargs)
        SmarterRequestMixin.__init__(self, *args, **kwargs)

    @property
    def loader(self) -> SAMLoader:
        """
        Get the SAMLoader instance. a SAMLoader instance is used to load
        raw manifest text into a Pydantic model. It performs cursory validations
        such as validating the file format, and identifying required dict key values
        such as the api version, the manifest kind and its name.
        """
        if not self._loader and self.manifest_data and not self._manifest_load_failed:
            try:
                self._loader = SAMLoader(
                    api_version=SMARTER_API_VERSION,
                    kind=self.manifest_kind,
                    manifest=self.manifest_data,
                )
                if not self._loader:
                    raise APIV1CLIViewError("")
            except APIV1CLIViewError:
                # not all endpoints require a manifest, so we
                # should fail gracefully if the manifest is not provided.
                self._manifest_load_failed = True

        return self._loader

    @property
    def params(self) -> dict[str, any]:
        """
        The query string parameters from the Django request object. This extracts
        the query string parameters from the request object and converts them to a
        dictionary. This is used in child views to pass optional command-line
        parameters to the broker.
        """
        if not self._params:
            self._params = QueryDict(self.smarter_request.META.get("QUERY_STRING", "")) or {}
        return self._params

    @property
    def BrokerClass(self) -> Type[AbstractBroker]:
        """
        Get the broker class for the manifest kind. This is used to
        instantiate a broker for the manifest kind.
        """
        if not self._BrokerClass:
            if self.manifest_kind:
                self._BrokerClass = Brokers.get_broker(self.manifest_kind)
            if not self._BrokerClass:
                raise APIV1CLIViewError(f"Could not find broker for {self.manifest_kind} manifest.")
        return self._BrokerClass

    @property
    def broker(self) -> AbstractBroker:
        """
        Use a loader to try to instantiate a broker. A broker is a class that
        implements the broker service pattern. It provides a service interface
        that 'brokers' the http request for the underlying object that provides
        the object-specific service (create, update, get, delete, etc).
        """
        if self.BrokerClass and not self._broker:
            BrokerClass = self.BrokerClass
            self._broker = BrokerClass(
                request=self.smarter_request,
                api_version=SMARTER_API_VERSION,
                name=self.manifest_name,
                kind=self.manifest_kind,
                account=self.user_profile.account if self.user_profile else None,
                loader=self.loader,
                manifest=self.loader.yaml_data if self.loader else None,
            )
            if not self._broker:
                raise APIV1CLIViewError("Could not load manifest.")

        return self._broker

    @property
    def manifest_data(self) -> json:
        """
        The raw manifest data from the request body. The manifest data is a json object
        which needs to be rendered into a Pydantic model. The Pydantic model is then
        used to instantiate a broker for the manifest kind.
        """
        if self._manifest_data:
            # belt & suspenders: ensure that the manifest data is a json object.
            if isinstance(self._manifest_data, str):
                self._manifest_data = json.loads(self._manifest_data)
        return self._manifest_data

    @property
    def manifest_name(self) -> str:
        """
        The name of the manifest. The manifest name is used to identify the resource
        within a Kind. For example, the manifest name for a ChatBot resource is the
        name of the chatbot. The manifest name is used to identify the resource
        within a Kind. The name can be passed from inside the raw manifest data, or
        it can be passed as part of a url path.

        Example url path with a name: /api/v1/cli/describe/chatbot/<str:name>/
        """
        if not self._manifest_name and self.manifest_data:
            self._manifest_name = self.manifest_data.get("metadata", {}).get("name", None)
        if not self._manifest_kind and self.loader:
            self._manifest_kind = self.loader.manifest_metadata.get("name") if self.loader else None
        return self._manifest_name

    @property
    def manifest_kind(self) -> str:
        """
        The kind of the manifest. The manifest kind is used to identify the type
        of resource that the manifest is describing. The kind is used to identify
        the broker that will be used to broker the http request for the resource.
        """
        if not self._manifest_kind and self.manifest_data:
            self._manifest_kind = str(self.manifest_data.get("kind", None))
        if not self._manifest_kind and self.loader:
            self._manifest_kind = str(self.loader.manifest_kind) if self.loader else None

        # if we still don't have a manifest kind, then we should
        # analyze the url path to determine the manifest kind.
        # urls:
        # - http://testserver/api/v1/cli/logs/Chatbot/?name=TestChatBot
        # - http://testserver/api/v1/cli/chat/config/TestChatBot/
        if not self._manifest_kind:
            self._manifest_kind = SAMKinds.from_url(self.url)
            if self._manifest_kind:
                logger.warning("setting manifest kind to %s from analysis of url %s", self._manifest_kind, self.url)

        # may or may not have a manifest kind at this point.
        # anti examples:
        # - http://testserver/api/v1/cli/whoami/
        # - http://testserver/api/v1/cli/apply/
        return self._manifest_kind

    @property
    def command(self) -> SmarterJournalCliCommands:
        """
        Translate the request route into a SmarterJournalCliCommands enum
        instance. For example, if the route is '/api/v1/cli/apply/', then
        the corresponding command will be SmarterJournalCliCommands.APPLY.

        url: http://testserver/api/v1/cli/logs/Chatbot/?name=TestChatBot
        """
        match = re.search(r"/cli/([^/]+)/", self.url or "")
        if match:
            _command = match.group(1)
            return SmarterJournalCliCommands(_command)
        raise APIV1CLIViewError(f"Could not determine command from url: {self.url}")

    # pylint: disable=too-many-return-statements,too-many-branches
    def dispatch(self, request, *args, **kwargs):
        """
        Dispatch method for the CliBaseApiView. We want to take care of as
        much housekeeping as possible in the base class. This includes
        setting following attributes:

        - manifest_name: the name identifier of the manifest could be passed
            from insider the raw manifest data, or it could be passed as part of a url.

        - manifest: the http request body might contain raw manifest text
            in yaml or json format. The manifest text is passed to the SAMLoader that will load,
            and partially validate and parse the manifest. This is then used to
            fully initialize a Pydantic manifest model. The Pydantic manifest
            model will be passed to a AbstractBroker for the manifest 'kind', which
            implements the broker service pattern for the underlying object.

        - kind: the kind of the manifest is used to identify the broker that will

        - user/account: the user, account and user_profile are all derived from the
            authenticated user in the Django request object.

        - command: the command is derived from the request path. The command is
            used to determine the type of operation that the view should perform.
            For example, if the url path is '/api/v1/cli/apply/', then the command
            will be SmarterJournalCliCommands.APPLY.

        - broker: the broker is a class that implements the broker service pattern.
            It provides a service interface that 'brokers' the http request for the
            underlying object that provides the object-specific service (create, update, get, delete, etc).
        """

        # this is a hacky way to get SmarterRequestMixin request object
        # initialized.
        super().init(request=request)

        # Manifest parsing and broker instantiation are lazy implementations.
        # So for now, we'll only set the private class variable _manifest_data
        # from the request body, and then we'll leave it to the child views to
        # decide if/when to actually parse the manifest and instantiate the broker.
        try:
            data = request.body.decode("utf-8")
            # if the command is 'chat', then the raw prompt text
            # or the encoded file attachment data will be in the request body.
            # otherwise, the request body should contain manifest text.
            if self.command == SmarterJournalCliCommands.CHAT:
                self._prompt = data
                self._manifest_kind = SAMKinds.CHAT.value
            else:
                self._manifest_data = json.loads(data)
        except json.JSONDecodeError:
            try:
                self._manifest_data = yaml.safe_load(data)
            except yaml.YAMLError as e:
                try:
                    raise APIV1CLIViewError("Could not parse manifest. Valid formats: yaml, json.") from e
                except APIV1CLIViewError as ex:
                    return SmarterJournaledJsonErrorResponse(
                        request=request,
                        thing=self.manifest_kind,
                        command=self.command,
                        e=ex,
                        status=HTTPStatus.BAD_REQUEST.value,
                    )

        try:
            AccountMixin.__init__(self, user=request.user)
            if self.user.is_authenticated and not self.user_profile:
                raise APIV1CLIViewError("Could not find account for user.")
        except SmarterExceptionBase as e:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=e,
                status=HTTPStatus.FORBIDDEN.value,
            )
        # Parse the query string parameters from the request into a dictionary.
        # This is used to pass additional parameters to the child view's post method.
        self._manifest_name = self.params.get("name", None)

        if self.authentication_classes and self.permission_classes:
            if not request.user.is_authenticated:
                try:
                    raise APIV1CLIViewError("Unauthorized access attempted.")
                except APIV1CLIViewError as e:
                    return SmarterJournaledJsonErrorResponse(
                        request=request,
                        thing=self.manifest_kind,
                        command=self.command,
                        e=e,
                        status=HTTPStatus.FORBIDDEN.value,
                    )

        user_agent = request.headers.get("User-Agent", "")
        if "Go-http-client" not in user_agent:
            logger.warning("The User-Agent is not a Go lang application: %s", user_agent)

        kind = kwargs.get("kind", None)
        if kind:
            self._manifest_kind = Brokers.get_broker_kind(kind)
            if not self.manifest_kind:
                return SmarterJournaledJsonErrorResponse(
                    request=request,
                    thing=self.manifest_kind,
                    command=self.command,
                    e=SAMBadRequestError(
                        f"Unsupported manifest kind: {self.manifest_kind}. should be one of {SAMKinds.all_values()}"
                    ),
                    status=HTTPStatus.BAD_REQUEST.value,
                )

        # generic exception handler that simply ensures that in all cases
        # the response is a JsonResponse with a status code.
        #
        # note that we are combining the dictionary of parameters with the
        # keyword arguments. This is because the keyword arguments are passed
        # to the super class dispatch method, and the parameters are passed
        # to the child view's post method.
        try:
            return super().dispatch(request, *args, **{**self.params, **kwargs})
        except SAMBrokerErrorNotImplemented as not_implemented_error:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=not_implemented_error.get_formatted_err_message,
                status=HTTPStatus.NOT_IMPLEMENTED.value,
            )
        except SAMBrokerErrorNotReady as not_ready_error:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=not_ready_error.get_formatted_err_message,
                status=HTTPStatus.SERVICE_UNAVAILABLE.value,
            )
        except SAMBrokerErrorNotFound as not_found_error:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=not_found_error.get_formatted_err_message,
                status=HTTPStatus.NOT_FOUND.value,
            )
        except SAMBrokerReadOnlyError as read_only_error:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=read_only_error.get_formatted_err_message,
                status=HTTPStatus.METHOD_NOT_ALLOWED.value,
            )
        except SAMBrokerError as broker_error:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=broker_error.get_formatted_err_message,
                status=HTTPStatus.BAD_REQUEST.value,
            )
        # pylint: disable=broad-except
        except Exception as e:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=e,
                status=HTTPStatus.INTERNAL_SERVER_ERROR.value,
            )
