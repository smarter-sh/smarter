"""Smarter API command-line interface Base class API view"""

import hashlib
import json
import logging
from http import HTTPStatus
from typing import Tuple, Type
from urllib.parse import urlencode

import yaml
from django.http import QueryDict
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView

from smarter.apps.account.mixins import AccountMixin
from smarter.apps.api.v1.cli.brokers import Brokers
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.api.v1.manifests.version import SMARTER_API_VERSION
from smarter.common.exceptions import SmarterExceptionBase
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonErrorResponse
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.exceptions import SAMBadRequestError
from smarter.lib.manifest.loader import SAMLoader


logger = logging.getLogger(__name__)


class APIV1CLIViewError(SmarterExceptionBase):
    """Base class for all APIV1CLIView errors."""

    @property
    def get_readable_name(self):
        return "Smarter api v1 command-line interface error"


# pylint: disable=too-many-instance-attributes
class CliBaseApiView(APIView, AccountMixin):
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

    _loader: SAMLoader = None
    _cache_key: str = None
    _broker: AbstractBroker = None
    _manifest_data: json = None
    _manifest_kind: str = None
    _manifest_name: str = None
    _manifest_load_failed: bool = False
    _BrokerClass: Type[AbstractBroker] = None
    _params: dict[str, any] = None
    _prompt: str = None

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
        if not self._params:
            self._params = QueryDict(self.request.META.get("QUERY_STRING", "")) or {}
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
                request=self.request,
                api_version=SMARTER_API_VERSION,
                name=self.manifest_name,
                kind=self.manifest_kind,
                account=self.user_profile.account,
                loader=self.loader,
                manifest=self.loader.yaml_data if self.loader else None,
            )
            if not self._broker:
                raise APIV1CLIViewError("Could not load manifest.")

        return self._broker

    @property
    def manifest_data(self) -> json:
        return self._manifest_data

    @property
    def manifest_name(self) -> str:
        if not self._manifest_name and self.manifest_data:
            self._manifest_name = self.manifest_data.get("metadata", {}).get("name", None)
        if not self._manifest_kind and self.loader:
            self._manifest_kind = self.loader.manifest_metadata.get("name") if self.loader else None
        return self._manifest_name

    @property
    def manifest_kind(self) -> str:
        if not self._manifest_kind and self.manifest_data:
            self._manifest_kind = str(self.manifest_data.get("kind", None))
        if not self._manifest_kind and self.loader:
            self._manifest_kind = str(self.loader.manifest_kind) if self.loader else None
        # resolve any inconsistencies in the casing of the manifest kind
        # that we might have received.
        # example: 'chatbot' vs 'ChatBot', 'plugin_data_sql_connection' vs 'PluginDataSqlConnection'
        return Brokers.get_broker_kind(self._manifest_kind)

    @property
    def command(self) -> SmarterJournalCliCommands:
        """
        Translate the request route into a SmarterJournalCliCommands enum
        instance. For example, if the route is '/api/v1/cli/apply/', then
        the command will be SmarterJournalCliCommands.APPLY.
        """

        def get_slug(path):
            parts = path.split("/")
            try:
                slug_index = parts.index("cli") + 1
                return parts[slug_index]
            except ValueError:
                return None

        this_command = get_slug(self.request.path)
        logger.info("command: %s", this_command)
        return SmarterJournalCliCommands(this_command)

    @property
    def prompt(self) -> str:
        return self._prompt

    @property
    def cache_key(self) -> str:
        """For cached values, get the cache key for the chat config view."""
        if not self._cache_key:
            raise APIV1CLIViewError("Internal error. Cache key has not been set.")
        return self._cache_key

    @cache_key.setter
    def cache_key(self, key_tuple: Tuple[str, str, str]) -> None:
        """
        Set a cache key based on a name string and a unique identifier 'uid'. This key is used to cache
        the session_key for the chat. The key is a combination of the class name,
        the chat name and the client UID. Currently used by the
        ApiV1CliChatConfigApiView and ApiV1CliChatApiView as a means of sharing the session_key.

        :param name: a generic object or resource name
        :param uid: UID of the client, assumed to have been created from the
         machine mac address and the hostname of the client
        """
        class_name, name, uid = key_tuple
        raw_string = class_name + "_" + name + "_" + uid
        hash_object = hashlib.sha256()
        hash_object.update(raw_string.encode())
        hash_string = hash_object.hexdigest()
        self._cache_key = hash_string

    @property
    def url(self) -> str:
        """Get the full url of the request. Reconstructs the exact url of the request."""
        return self.request.build_absolute_uri()

    # pylint: disable=too-many-return-statements,too-many-branches
    def dispatch(self, request, *args, **kwargs):
        """
        The http request body is expected to contain the manifest text
        in yaml format. The manifest text is passed to the SAMLoader that will load,
        and partially validate and parse the manifest. This is then used to
        fully initialize a Pydantic manifest model. The Pydantic manifest
        model will be passed to a AbstractBroker for the manifest 'kind', which
        implements the broker service pattern for the underlying object.
        """
        # Parse the query string parameters from the request into a dictionary.
        # This is used to pass additional parameters to the child view's post method.
        self._manifest_name = self.params.get("name", None)

        # TO DO: This is a temporary fix to mitigate a configuration issue
        # where DRF is not properly authenticating the request. This is a
        # temporary fix until we can properly configure the DRF authentication
        if not hasattr(request, "auth"):
            request.auth = SmarterTokenAuthentication()
            try:
                user, _ = request.auth.authenticate(request)
                request.user = user
            except AuthenticationFailed:
                try:
                    raise APIV1CLIViewError("Authentication failed.") from None
                except APIV1CLIViewError as e:
                    return SmarterJournaledJsonErrorResponse(
                        request=request, thing=self.manifest_kind, command=None, e=e, status=HTTPStatus.FORBIDDEN
                    )
        if not request.user.is_authenticated:
            try:
                raise APIV1CLIViewError("Authentication failed.")
            except APIV1CLIViewError as e:
                return SmarterJournaledJsonErrorResponse(
                    request=request, thing=self.manifest_kind, command=None, e=e, status=HTTPStatus.FORBIDDEN
                )

        # set all of our identifying attributes from the request.
        try:
            self._user = user = request.user
            if not self.user_profile:
                raise APIV1CLIViewError("Could not find account for user.")
        except SmarterExceptionBase as e:
            return SmarterJournaledJsonErrorResponse(
                request=request, thing=self.manifest_kind, command=None, e=e, status=HTTPStatus.FORBIDDEN
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
                    command=None,
                    e=SAMBadRequestError(
                        f"Unsupported manifest kind: {self.manifest_kind}. should be one of {SAMKinds.all_values()}"
                    ),
                    status=HTTPStatus.BAD_REQUEST,
                )

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
                        request=request, thing=self.manifest_kind, command=None, e=ex, status=HTTPStatus.BAD_REQUEST
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
        # pylint: disable=broad-except
        except Exception as e:
            return SmarterJournaledJsonErrorResponse(
                request=request,
                thing=self.manifest_kind,
                command=self.command,
                e=e,
                status=HTTPStatus.INTERNAL_SERVER_ERROR,
            )
