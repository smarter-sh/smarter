# pylint: disable=W0718
"""Smarter Api ApiConnection Manifest handler"""

import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.models import Secret
from smarter.apps.plugin.manifest.enum import (
    SAMApiConnectionSpecConnectionKeys,
    SAMApiConnectionSpecKeys,
    SAMApiConnectionStatusKeys,
)
from smarter.apps.plugin.manifest.models.api_connection.enum import AuthMethods
from smarter.apps.plugin.manifest.models.api_connection.spec import SAMApiConnectionSpec
from smarter.apps.plugin.manifest.models.common.connection.metadata import (
    SAMConnectionCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.connection.status import (
    SAMConnectionCommonStatus,
)
from smarter.apps.plugin.models import ApiConnection
from smarter.apps.plugin.serializers import ApiConnectionSerializer
from smarter.common.conf import settings as smarter_settings
from smarter.common.utils import camel_to_snake
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import (
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)

from ..models.api_connection.const import MANIFEST_KIND
from ..models.api_connection.model import SAMApiConnection
from . import SAMConnectionBrokerError
from .connection_base import SAMConnectionBaseBroker


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING)
        or waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMApiConnectionBroker(SAMConnectionBaseBroker):
    """
    Smarter API ApiConnection Manifest Broker.

    This class is responsible for loading, validating, and parsing Smarter API YAML ApiConnection manifests, and initializing the corresponding Pydantic model. It provides generic services for ApiConnection objects, including instantiation, creation, update, and deletion.

    :param loader: Manifest loader providing manifest data.
    :type loader: Optional[ManifestLoader]
    :param account: The account context for the connection.
    :type account: Account
    :param user_profile: The user profile associated with the connection.
    :type user_profile: UserProfile

    .. seealso::

        :class:`SAMApiConnection`
        :class:`ApiConnection`
        :class:`ApiConnectionSerializer`
        :class:`SAMConnectionBrokerError`

    **Example usage**::

        broker = SAMApiConnectionBroker(loader=my_loader, account=my_account, user_profile=my_profile)
        manifest = broker.manifest
        orm_data = broker.manifest_to_django_orm()

    """

    # override the base abstract manifest model with the ApiConnection model
    _manifest: Optional[SAMApiConnection] = None
    _pydantic_model: Type[SAMApiConnection] = SAMApiConnection
    _connection: Optional[ApiConnection] = None
    _api_key_secret: Optional[Secret] = None
    _proxy_password_secret: Optional[Secret] = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def serializer(self) -> Type[ApiConnectionSerializer]:
        """
        Return the serializer class for the broker.

        This property provides the serializer used to convert ApiConnection model instances to and from native Python datatypes, enabling validation and serialization for API responses and internal processing.

        :return: The serializer class for ApiConnection objects.
        :rtype: Type[ApiConnectionSerializer]

        .. seealso::

            :class:`ApiConnectionSerializer`
            :class:`ApiConnection`
            :meth:`SAMApiConnectionBroker.manifest`
            :meth:`SAMApiConnectionBroker.manifest_to_django_orm`

        **Example usage**::

            serializer_cls = broker.serializer
            serializer = serializer_cls(api_connection_instance)
            data = serializer.data

        """
        return ApiConnectionSerializer

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.

        This property generates a human-readable class name string for use in log messages, making it easier to identify the source of log entries. It appends the specific broker class to the parent class name for clarity.

        :return: Formatted class name string for logging.
        :rtype: str

        .. important::

            Use this property in log statements to improve traceability and debugging.

        .. seealso::

            :meth:`SAMApiConnectionBroker.serializer`
            :meth:`SAMApiConnectionBroker.manifest`
            :meth:`SAMApiConnectionBroker.model_class`

        **Example usage**::

            logger.info("%s: operation started", broker.formatted_class_name)

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{self.__class__.__name__}()"

    @property
    def model_class(self) -> Type[ApiConnection]:
        """
        Return the Django ORM model class for ApiConnection.

        This property provides the class object used for persistent storage and manipulation of API connection data in the database. It is useful for type checking, introspection, and for creating or querying ApiConnection instances.

        :return: The Django ORM model class for API connections.
        :rtype: Type[ApiConnection]

        .. seealso::

            :class:`ApiConnection`
            :meth:`SAMApiConnectionBroker.serializer`
            :meth:`SAMApiConnectionBroker.manifest`

        **Example usage**::

            model_cls = broker.model_class
            all_connections = model_cls.objects.all()

        """
        return ApiConnection

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMApiConnection]:
        """
        Returns the manifest as a Pydantic model representing the Smarter API ApiConnection manifest.

        This property initializes and returns a ``SAMApiConnection`` Pydantic model using data
        loaded from the manifest loader. The manifest loader provides the manifest's API version,
        kind, metadata, spec, and status, which are passed to the model constructor.

        The top-level manifest model must be explicitly initialized, while child models
        (such as metadata, spec, and status) are automatically cascade-initialized by Pydantic,
        passing the relevant data to each child's constructor.

        If the loader's manifest kind does not match the expected kind, a warning is logged
        and the manifest is not initialized.

        :return: The manifest as a ``SAMApiConnection`` Pydantic model, or ``None`` if not initialized.
        :rtype: Optional[SAMApiConnection]
        """
        if not self._manifest and self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMApiConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata) if self.loader else None,
                spec=SAMApiConnectionSpec(**self.loader.manifest_spec) if self.loader else None,
                status=(
                    SAMConnectionCommonStatus(**self.loader.manifest_status)
                    if self.loader and self.loader.manifest_status
                    else None
                ),
            )
            logger.info("%s.manifest() initialized manifest from loader", self.formatted_class_name)
        else:
            logger.warning(
                "%s.manifest() could not initialize manifest. Expected %s but got %s",
                self.formatted_class_name,
                self.kind,
                self.loader.manifest_kind if self.loader else None,
            )
        return self._manifest

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API User manifest into a Django ORM model.

        This method converts the validated manifest data into a dictionary suitable for creating or updating a Django ORM `ApiConnection` instance. It handles field mapping, type conversion, and secret resolution for sensitive fields such as API keys and proxy passwords.

        :returns: Dictionary of ORM-compatible fields for an `ApiConnection` model.
        :rtype: dict

        .. note::

            - The returned dictionary includes all required fields for ORM persistence, with secrets resolved to their database IDs.
            - The method automatically converts camelCase keys to snake_case for Django compatibility.

        :raises SAMConnectionBrokerError:
            If the manifest or its spec is missing or malformed

        .. seealso::

            :class:`ApiConnection`
            :meth:`SAMApiConnectionBroker.manifest`
            :meth:`SAMApiConnectionBroker.serializer`

        **Example usage**::

            orm_data = broker.manifest_to_django_orm()
            connection = ApiConnection(**orm_data)
            connection.save()

        """
        config_dump = self.manifest.spec.connection.model_dump() if self.manifest and self.manifest.spec else None
        if not isinstance(config_dump, dict):
            raise SAMConnectionBrokerError(
                f"Manifest spec.connection is not a dict: {type(config_dump)}",
                thing=self.kind,
            )

        config_dump = self.camel_to_snake(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMConnectionBrokerError(
                f"Manifest spec.connection is not a dict: {type(config_dump)}",
                thing=self.kind,
            )
        config_dump[SAMMetadataKeys.NAME.value] = (
            self.manifest.metadata.name if self.manifest and self.manifest.metadata else None
        )
        config_dump[SAMMetadataKeys.DESCRIPTION.value] = (
            self.manifest.metadata.description if self.manifest and self.manifest.metadata else None
        )
        config_dump[SAMMetadataKeys.VERSION.value] = (
            self.manifest.metadata.version if self.manifest and self.manifest.metadata else None
        )
        config_dump[SAMKeys.KIND.value] = self.kind

        if not self.user_profile:
            raise SAMConnectionBrokerError(
                "User profile is not set. Cannot retrieve or create secrets.",
                thing=self.kind,
            )

        # retrieve the apiKey Secret
        api_key_name = camel_to_snake(SAMApiConnectionSpecConnectionKeys.API_KEY.value)
        if api_key_name:
            try:
                secret = Secret.objects.get(name=api_key_name, user_profile=self.user_profile)
                config_dump[SAMApiConnectionSpecConnectionKeys.API_KEY.value] = secret.id  # type: ignore[assignment]
            except Secret.DoesNotExist:
                logger.warning(
                    "%s.manifest_to_django_orm() api key Secret %s not found for user %s",
                    self.formatted_class_name,
                    api_key_name,
                    self.user_profile.user.username,
                )

        # retrieve the proxyUsername Secret, if it exists
        proxy_password_name = camel_to_snake(SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value)
        if proxy_password_name:
            try:
                secret = Secret.objects.get(name=proxy_password_name, user_profile=self.user_profile)
                config_dump[SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value] = secret.id  # type: ignore[assignment]
            except Secret.DoesNotExist:
                logger.warning(
                    "%s.manifest_to_django_orm() proxy password Secret %s not found for user %s",
                    self.formatted_class_name,
                    proxy_password_name,
                    self.user_profile.user.username,
                )

        return config_dump

    @property
    def api_key_secret(self) -> Optional[Secret]:
        """
        Return the api_key secret for the ApiConnection.

        This property retrieves the Django ORM `Secret` instance associated with the API key for the current connection. It resolves the secret either from the manifest or from the existing database record, depending on initialization context.

        :return: The `Secret` object representing the API key, or `None` if not found.
        :rtype: Optional[Secret]

        .. attention::

            If the secret cannot be found, a warning is logged and `None` is returned.

        .. seealso::

            :class:`Secret`
            :meth:`SAMApiConnectionBroker.manifest`
            :meth:`SAMApiConnectionBroker.connection`

        **Example usage**::

            api_key_secret = broker.api_key_secret
            if api_key_secret:
                print(api_key_secret.value)

        """
        if self._api_key_secret:
            return self._api_key_secret
        try:
            name = (
                self.manifest.spec.connection.apiKey
                if self.manifest and self.manifest.spec
                else self.connection.api_key.name if self.connection and self.connection.api_key else None
            )
            self._api_key_secret = Secret.objects.get(
                user_profile=self.user_profile,
                name=name,
            )
            return self._api_key_secret
        except Secret.DoesNotExist:
            logger.warning(
                "%s api_key Secret %s not found for account %s",
                self.formatted_class_name,
                name or "(name is missing)",
                self.account,
            )
        return None

    @property
    def proxy_password_secret(self) -> Optional[Secret]:
        """
        Return the proxy password secret for the ApiConnection.

        This property retrieves the Django ORM `Secret` instance associated with the proxy password for the current connection. It resolves the secret either from the manifest or from the existing database record, depending on initialization context.

        :return: The `Secret` object representing the proxy password, or `None` if not found.
        :rtype: Optional[Secret]

        .. attention::

            - If the secret cannot be found, a warning is logged and `None` is returned.

        .. seealso::

            :class:`Secret`
            :meth:`SAMApiConnectionBroker.manifest`
            :meth:`SAMApiConnectionBroker.connection`

        **Example usage**::

            proxy_secret = broker.proxy_password_secret
            if proxy_secret:
                print(proxy_secret.value)

        """
        if self._proxy_password_secret:
            return self._proxy_password_secret
        try:
            name = (
                self.manifest.spec.connection.proxyPassword
                if self.manifest and self.manifest.spec
                else (
                    self.connection.proxy_password.name if self.connection and self.connection.proxy_password else None
                )
            )
            self._proxy_password_secret = Secret.objects.get(
                user_profile=self.user_profile,
                name=name,
            )
            return self._proxy_password_secret
        except Secret.DoesNotExist:
            logger.warning(
                "%s proxy password Secret %s not found for account %s",
                self.formatted_class_name,
                name or "(name is missing)",
                self.account,
            )
        return None

    @property
    def connection(self) -> Optional[ApiConnection]:
        """
        Return the Django ORM `ApiConnection` instance for this broker.

        This property retrieves the current `ApiConnection` object from the database using the account and name. If the connection does not exist, it attempts to create one from the manifest data. The returned object represents the persistent state of the API connection.

        :return: The `ApiConnection` ORM instance, or `None` if not found or not created.
        :rtype: Optional[ApiConnection]


        .. attention::

            - If the connection cannot be found or created, an error is logged and `None` is returned.

        .. seealso::

            :class:`ApiConnection`
            :meth:`SAMApiConnectionBroker.manifest`
            :meth:`SAMApiConnectionBroker.manifest_to_django_orm`
            :meth:`SAMApiConnectionBroker.api_key_secret`
            :meth:`SAMApiConnectionBroker.proxy_password_secret`

        **Example usage**::

            connection = broker.connection
            if connection:
                print(connection.base_url)
                connection.timeout = 60
                connection.save()

        """
        if self._connection:
            return self._connection

        try:
            name = self.camel_to_snake(self.name)  # type: ignore
            self._connection = ApiConnection.objects.get(account=self.account, name=name)
        except ApiConnection.DoesNotExist as e:
            if self.manifest:
                model_dump = (
                    self.manifest.spec.connection.model_dump() if self.manifest and self.manifest.spec else None
                )
                model_dump = self.camel_to_snake(model_dump) if isinstance(model_dump, dict) else model_dump
                if not isinstance(model_dump, dict):
                    raise SAMConnectionBrokerError(
                        f"Manifest spec.connection is not a dict: {type(model_dump)}",
                        thing=self.kind,
                    ) from e
                model_dump[SAMMetadataKeys.ACCOUNT.value] = self.account
                model_dump[SAMMetadataKeys.NAME.value] = (
                    self.manifest.metadata.name if self.manifest and self.manifest.metadata else None
                )
                model_dump[SAMMetadataKeys.VERSION.value] = (
                    self.manifest.metadata.version if self.manifest and self.manifest.metadata else None
                )
                model_dump[SAMMetadataKeys.DESCRIPTION.value] = (
                    self.manifest.metadata.description if self.manifest and self.manifest.metadata else None
                )
                model_dump[SAMKeys.KIND.value] = self.kind
                model_dump["api_key"] = self.api_key_secret

                self._connection = ApiConnection(**model_dump)
                self._connection.save()
                self._created = True
            else:
                logger.error(
                    "%s ApiConnection %s not found for account %s",
                    self.formatted_class_name,
                    self.name or "(name is missing)",
                    self.account or "(account is missing)",
                )

        return self._connection

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example ApiConnection manifest.

        This method generates and returns a sample manifest for an ApiConnection, including all required fields and example values for authentication, connection, and metadata. The manifest is validated using the Pydantic model and returned as a JSON response.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response containing the example manifest.
        :rtype: SmarterJournaledJsonResponse

        .. seealso::

            :class:`SAMApiConnection`
            :class:`ApiConnection`
            :class:`ApiConnectionSerializer`
            :class:`AuthMethods`
            :class:`SAMKeys`
            :class:`SAMMetadataKeys`
            :class:`SAMApiConnectionSpecConnectionKeys`
            :class:`SmarterJournalCliCommands`

        **Example usage**::

            response = broker.example_manifest(request)
            print(response.data)

        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "example_connection",
                SAMMetadataKeys.DESCRIPTION.value: f"Example {self.kind} using any of the following authentication methods: {AuthMethods.all_values()}",
                SAMMetadataKeys.VERSION.value: "0.1.0",
            },
            SAMKeys.SPEC.value: {
                SAMApiConnectionSpecKeys.CONNECTION.value: {
                    SAMApiConnectionSpecConnectionKeys.BASE_URL.value: "http://localhost:8000/",
                    SAMApiConnectionSpecConnectionKeys.API_KEY.value: "12345-abcde-67890-fghij",
                    SAMApiConnectionSpecConnectionKeys.AUTH_METHOD.value: "token",
                    SAMApiConnectionSpecConnectionKeys.TIMEOUT.value: 30,
                    SAMApiConnectionSpecConnectionKeys.PROXY_PROTOCOL.value: "http",
                    SAMApiConnectionSpecConnectionKeys.PROXY_HOST.value: "proxy.example.com",
                    SAMApiConnectionSpecConnectionKeys.PROXY_PORT.value: 8080,
                    SAMApiConnectionSpecConnectionKeys.PROXY_USERNAME.value: "proxyuser",
                    SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value: "proxypass",
                }
            },
        }
        # validate our results by round-tripping the data through the Pydantic model
        pydantic_model = self.pydantic_model(**data)
        data = json.loads(pydantic_model.model_dump_json())
        return self.json_response_ok(command=command, data=data)

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve a list of ApiConnection objects as a journaled JSON response.

        This method queries the database for `ApiConnection` instances matching the current account and optional name filter, serializes each result, and returns a structured JSON response including metadata, item count, and model titles.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Optional keyword arguments, such as `name` to filter connections.
        :type kwargs: dict
        :return: Journaled JSON response containing serialized ApiConnection data.
        :rtype: SmarterJournaledJsonResponse

        .. seealso::

            :class:`ApiConnection`
            :class:`ApiConnectionSerializer`
            :class:`SmarterJournaledJsonResponse`
            :meth:`SAMApiConnectionBroker.serializer`

        **Example usage**::

            response = broker.get(request)
            print(response.data)

            # Filter by name
            response = broker.get(request, name="my_connection")
            print(response.data)


        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name: Optional[str] = kwargs.get(SAMMetadataKeys.NAME.value, None)
        data = []

        # generate a QuerySet of ApiConnection objects that match our search criteria
        if name:
            api_connections = ApiConnection.objects.filter(account=self.account, name=name)
        else:
            api_connections = ApiConnection.objects.filter(account=self.account)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each ApiConnection
        for api_connection in api_connections:
            try:
                model_dump = self.serializer(api_connection).data
                if not model_dump:
                    raise SAMConnectionBrokerError(
                        f"Model dump failed for {self.kind} {api_connection.name}", thing=self.kind, command=command
                    )
                data.append(model_dump)
            except Exception as e:
                raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=self.serializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest. Copy the manifest data to the Django ORM model and
        save the model to the database.

        This method calls :meth:`super().apply` to ensure that the manifest is loaded
        and validated before applying the manifest to the Django ORM model.

        Note that there are fields included in the manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the ``save()`` command. These fields are defined in the ``readonly_fields`` list.

        Example manifest structure::

            {
                "apiVersion": "smarter.sh/v1",          # read only
                "kind": "ApiConnection",                # read only
                "metadata": {                           # updated in super().apply()
                    "name": "testf232a0619cb19da0",
                    "description": "new description",
                    "version": "1.0.0"
                },
                "spec": {                               # updated here.
                    "connection": {
                        "kind": "ApiConnection",
                        "version": "1.0.0",
                        "account": "2194-1233-0815",
                        "baseUrl": "http://localhost:8000/api/v1/cli/example_manifest/plugin/",
                        "apiKey": "testf232a0619cb19da0",
                        "authMethod": "basic",
                        "timeout": 30,
                        "proxyProtocol": "http",
                        "proxyHost": null,
                        "proxyPort": null,
                        "proxyUsername": null,
                        "proxyPassword": null
                    }
                },
                "status": {                             # read only
                    "connection_string": "http://localhost:8000/api/v1/cli/example_manifest/plugin/ (Auth: ******)",
                    "is_valid": false
                }
            }

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating success and the updated manifest data.
        :rtype: SmarterJournaledJsonResponse
        :raises SAMConnectionBrokerError: If an error occurs during update or save.
        """
        super().apply(request, kwargs)
        updated = False
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        readonly_fields = ["id", "created_at", "updated_at"]

        # update the spec
        api_key_name = camel_to_snake(SAMApiConnectionSpecConnectionKeys.API_KEY.value)
        proxy_password_name = camel_to_snake(SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value)
        data = self.manifest_to_django_orm()
        for field in readonly_fields:
            data.pop(field, None)

        try:
            for key, value in data.items():
                if key == api_key_name:
                    if self.api_key_secret and key != self.api_key_secret.id:  # type: ignore[comparison-overlap]
                        setattr(self.connection, key, self.api_key_secret)
                        logger.info("%s.apply() setting api_key Secret <Fk> to %s", self.formatted_class_name, value)
                        updated = True
                elif key == proxy_password_name:
                    if self.proxy_password_secret and key != self.proxy_password_secret.id:  # type: ignore[comparison-overlap]
                        setattr(self.connection, key, self.proxy_password_secret)
                        logger.info(
                            "%s.apply() setting proxy_password Secret <Fk> to %s",
                            self.formatted_class_name,
                            value,
                        )
                        updated = True
                else:
                    if key != value:
                        setattr(self.connection, key, value)
                        logger.info("%s.apply() updating %s to %s", self.formatted_class_name, key, value)
                        updated = True

            if updated and isinstance(self.connection, ApiConnection):
                self.connection.save()
                logger.info(
                    "%s.apply() updated ApiConnection %s",
                    self.formatted_class_name,
                    self.serializer(self.connection).data,
                )
        except Exception as e:
            raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Handle chat operations for the API connection broker.

        This method is intended to process chat requests using the manifest broker. Currently, it is not implemented and will always raise a `SAMBrokerErrorNotImplemented` exception.
        This method is not implemented. Any invocation will result in an error.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: SAMBrokerErrorNotImplemented. This method always raises an exception.
        :rtype: SmarterJournaledJsonResponse

        .. seealso::

            :class:`SAMApiConnectionBroker`
            :class:`SmarterJournalCliCommands`
            :class:`SAMBrokerErrorNotImplemented`

        **Example usage**::

            try:
                response = broker.chat(request)
            except SAMBrokerErrorNotImplemented as e:
                print("Chat not implemented:", e)


        """
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response containing the manifest data for the current API connection.

        This method serializes the manifest and connection details, including metadata, specification, and status, into a structured JSON response. It validates the connection and includes relevant fields such as connection string and validity status.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response with manifest data.
        :rtype: SmarterJournaledJsonResponse

        :raises SAMBrokerErrorNotReady:
            If no connection is found

        :raises SAMConnectionBrokerError:
            if serialization or validation fails.

        .. seealso::

            :class:`SAMApiConnection`
            :class:`ApiConnection`
            :class:`SmarterJournaledJsonResponse`
            :meth:`SAMApiConnectionBroker.connection`

        **Example usage**::

            response = broker.describe(request)
            print(response.data)


        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        is_valid = False
        try:
            if isinstance(self.connection, SAMApiConnection):
                is_valid = self.connection.validate()
        except Exception:
            pass

        if self.connection is None:
            raise SAMBrokerErrorNotReady(message="No connection found", thing=self.kind, command=command)

        try:
            data = model_to_dict(self.connection)
            data = self.snake_to_camel(data)
            if not isinstance(data, dict):
                raise SAMConnectionBrokerError(
                    f"Model dump failed for {self.kind} {self.connection.name}",
                    thing=self.kind,
                    command=command,
                )
            data.pop("id")
            data.pop(SAMMetadataKeys.NAME.value)
            data[SAMMetadataKeys.ACCOUNT.value] = self.connection.account.account_number
            data.pop(SAMMetadataKeys.DESCRIPTION.value)
            data[SAMApiConnectionSpecConnectionKeys.API_KEY.value] = (
                self.api_key_secret.name if self.api_key_secret else None
            )
            data[SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value] = (
                self.proxy_password_secret.name if self.proxy_password_secret else None
            )

            retval = {
                SAMKeys.APIVERSION.value: self.api_version,
                SAMKeys.KIND.value: self.kind,
                SAMKeys.METADATA.value: {
                    SAMMetadataKeys.NAME.value: self.connection.name,
                    SAMMetadataKeys.DESCRIPTION.value: self.connection.description,
                    SAMMetadataKeys.VERSION.value: self.connection.version,
                },
                SAMKeys.SPEC.value: {SAMApiConnectionSpecKeys.CONNECTION.value: data},
                SAMKeys.STATUS.value: {
                    SAMApiConnectionStatusKeys.CONNECTION_STRING.value: self.connection.connection_string,
                    SAMApiConnectionStatusKeys.IS_VALID.value: is_valid,
                },
            }
            # validate our results by round-tripping the data through the Pydantic model
            pydantic_model = self.pydantic_model(**retval)
            data = pydantic_model.model_dump_json()
            return self.json_response_ok(command=command, data=retval)
        except Exception as e:
            raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the current API connection and return a JSON response indicating the result.

        This method attempts to delete the associated `ApiConnection` object from the database. If successful, it returns an empty JSON response. If no connection exists, or if an error occurs during deletion, an appropriate exception is raised.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: JSON response indicating deletion success.
        :rtype: SmarterJournaledJsonResponse

        :raises SAMBrokerErrorNotReady:
            If no connection is found to delete.

        :raises SAMConnectionBrokerError:
            If an error occurs during deletion.

        .. error::
            Any exception during deletion is wrapped and raised as :class:`SAMConnectionBrokerError`.

        .. seealso::

            :class:`ApiConnection`
            :class:`SmarterJournaledJsonResponse`
            :meth:`SAMApiConnectionBroker.connection`

        **Example usage**::

            response = broker.delete(request)
            print(response.data)

        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.connection:
            try:
                self.connection.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="No connection found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Handle deploy operations for the API connection broker.
        This is not implemented and will always raise a `SAMBrokerErrorNotImplemented` exception.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: SAMBrokerErrorNotImplemented. This method always raises an exception.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Handle undeploy operations for the API connection broker.
        This is not implemented and will always raise a `SAMBrokerErrorNotImplemented` exception.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: SAMBrokerErrorNotImplemented. This method always raises an exception.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Handle logs operations for the API connection broker.
        This is not implemented and will always raise a `SAMBrokerErrorNotImplemented` exception.

        :param request: Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.
        :return: SAMBrokerErrorNotImplemented. This method always raises an exception.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Logs not implemented", thing=self.kind, command=command)
