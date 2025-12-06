# pylint: disable=W0718
"""Smarter Api SqlConnection Manifest handler"""

import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.models import Secret
from smarter.apps.plugin.manifest.enum import (
    SAMSqlConnectionSpecConnectionKeys,
    SAMSqlConnectionSpecKeys,
    SAMSqlConnectionStatusKeys,
)
from smarter.apps.plugin.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.plugin.models import SqlConnection
from smarter.apps.plugin.serializers import SqlConnectionSerializer
from smarter.common.conf import settings as smarter_settings
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

from ..models.common.connection.metadata import SAMConnectionCommonMetadata
from ..models.sql_connection.const import MANIFEST_KIND
from ..models.sql_connection.model import SAMSqlConnection
from ..models.sql_connection.spec import SAMSqlConnectionSpec
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


class SAMSqlConnectionBroker(SAMConnectionBaseBroker):
    """
    Broker for Smarter API SQL Connection manifests.

    This class is responsible for loading, validating, and parsing Smarter API YAML SqlConnection manifests,
    and initializing the corresponding Pydantic model. It provides generic services for SQL connections,
    such as instantiation, creation, update, and deletion.

    **Parameters:**

        - manifest (SAMSqlConnection, optional): The loaded manifest model.
        - pydantic_model (Type[SAMSqlConnection]): The Pydantic model class for validation.
        - connection (SqlConnection, optional): The Django ORM model instance.
        - password_secret (Secret, optional): Secret for the database password.
        - proxy_password_secret (Secret, optional): Secret for the proxy password.

    **Example Usage:**

        .. code-block:: python

            broker = SAMSqlConnectionBroker()
            manifest = broker.manifest  # Returns the loaded manifest as a Pydantic model
            orm_dict = broker.manifest_to_django_orm()  # Converts manifest to Django ORM dict

    .. seealso::

        - :class:`SAMConnectionBaseBroker`
        - :class:`SAMSqlConnection`
        - :class:`SqlConnection`

    **Raises:**

        - SAMBrokerErrorNotReady: If required parameters (e.g., user profile, manifest) are missing.
        - SAMConnectionBrokerError: For invalid connection data or failed operations.

    .. important::

        This broker caches loaded manifests and connections for efficiency. Always check for existence before accessing properties.

    """

    # override the base abstract manifest model with the SqlConnection model
    _manifest: Optional[SAMSqlConnection] = None
    _pydantic_model: Type[SAMSqlConnection] = SAMSqlConnection
    _connection: Optional[SqlConnection] = None
    _password_secret: Optional[Secret] = None
    _proxy_password_secret: Optional[Secret] = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def serializer(self) -> Type[SqlConnectionSerializer]:
        """
        Returns the serializer class used by the broker for SQL connection objects.

        This property provides the appropriate serializer for converting `SqlConnection` ORM instances
        to and from Python data structures, typically for API responses or internal processing.

        :returns: The serializer class (`SqlConnectionSerializer`) for SQL connection objects.

        .. seealso::

            - :class:`SqlConnectionSerializer`
            - :class:`SqlConnection`

        **Example Usage:**

            .. code-block:: python

                serializer_cls = broker.serializer
                serializer = serializer_cls(sql_connection_instance)
                data = serializer.data

        """
        return SqlConnectionSerializer

    @property
    def formatted_class_name(self) -> str:
        """
        Returns a formatted class name string for logging.

        This property generates a readable class name, including its parent class, to improve log clarity
        and traceability. Useful for debugging and monitoring, especially in complex inheritance scenarios.

        :returns: A string representing the fully qualified class name, e.g. ``ParentClass.SAMSqlConnectionBroker()``.

        .. seealso::

            - :meth:`SAMConnectionBaseBroker.formatted_class_name`

        **Example Usage:**

            .. code-block:: python

                logger.info(broker.formatted_class_name)
                # Output: ParentClass.SAMSqlConnectionBroker()

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.{self.__class__.__name__}()"

    @property
    def model_class(self) -> Type[SqlConnection]:
        """
        Returns the Django ORM model class associated with this broker.

        This property provides the concrete model used for SQL connection objects in the database.
        It is essential for operations that require direct interaction with the ORM, such as queries,
        creation, updates, and deletions.

        :returns: The Django model class (`SqlConnection`) for SQL connection records.


        .. seealso::

            - :class:`SqlConnection`
            - :meth:`serializer`

        **Example Usage:**

            .. code-block:: python

                model_cls = broker.model_class
                queryset = model_cls.objects.filter(account=account)


        """
        return SqlConnection

    @property
    def kind(self) -> str:
        """
        Returns the manifest kind string for this broker.

        This property identifies the type of manifest handled by the broker, which is used for validation,
        routing, and manifest processing logic. The value is typically a constant defined for the SQL connection manifest.

        :returns: The manifest kind string (e.g., ``"SqlConnection"``).

        .. seealso::

            - :data:`MANIFEST_KIND`
            - :meth:`manifest`

        **Example Usage:**

            .. code-block:: python

                if broker.kind == "SqlConnection":
                    # Proceed with SQL connection-specific logic

        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSqlConnection]:
        """
        Returns the manifest for the SQL connection as a `SAMSqlConnection` Pydantic model.

        This property loads and initializes the top-level manifest model for a SQL connection.
        If the manifest has already been loaded, it is returned from cache. Otherwise, if the loader is available
        and its manifest kind matches, a new `SAMSqlConnection` model is constructed using the manifest data
        provided by the loader.

        Child models within the manifest are automatically initialized by Pydantic when the top-level model is constructed.

        :returns: The manifest as a `SAMSqlConnection` instance, or `None` if not available.

        .. important::

            The manifest is cached after initial load for performance. If you need to reload the manifest,
            you must clear the cache manually.

        .. seealso::

            - :class:`SAMSqlConnection`
            - :meth:`manifest_to_django_orm`
            - :data:`MANIFEST_KIND`
            - :class:`SAMConnectionCommonMetadata`
            - :class:`SAMSqlConnectionSpec`

        **Example Usage:**

            .. code-block:: python

                manifest = broker.manifest
                if manifest:
                    print(manifest.metadata.name)

        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMSqlConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlConnectionSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API user manifest into a Django ORM model dictionary.

        This method converts the loaded and validated manifest (Pydantic model) into a dictionary
        suitable for creating or updating a `SqlConnection` Django ORM instance. It handles field
        name conversions, secret resolution, and metadata population.

        :returns: A dictionary representing the ORM model fields and values.

        :raises SAMBrokerErrorNotReady:
            If the user profile or manifest/connection spec is not set.
        :raises SAMConnectionBrokerError:
            If the manifest data is invalid or cannot be converted.

        .. important::

            This method will resolve and attach password and proxy password secrets as model fields.
            Read-only fields (such as ``id``, ``created_at``, ``updated_at``) are not included in the result.


        .. seealso::

            - :meth:`manifest`
            - :class:`SqlConnection`
            - :class:`Secret`

        **Example Usage:**

            .. code-block:: python

                orm_dict = broker.manifest_to_django_orm()
                connection = SqlConnection(**orm_dict)
                connection.save()

        """
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady(
                message="No user profile set for the broker",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        if self.manifest is None or self.manifest.spec.connection is None:
            raise SAMBrokerErrorNotReady(
                message="Manifest or connection spec is not set",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        connection = self.manifest.spec.connection.model_dump()  # type: ignore
        connection = self.camel_to_snake(connection)
        if not isinstance(connection, dict):
            raise SAMConnectionBrokerError(
                message=f"Invalid connection data: {connection}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        connection[SAMMetadataKeys.NAME.value] = self.manifest.metadata.name
        connection[SAMMetadataKeys.DESCRIPTION.value] = self.manifest.metadata.description
        connection[SAMMetadataKeys.VERSION.value] = self.manifest.metadata.version
        connection[SAMKeys.KIND.value] = self.kind

        # retrieve the password Secret
        password = self.camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PASSWORD.value)
        connection[SAMSqlConnectionSpecConnectionKeys.PASSWORD.value] = self.get_or_create_secret(
            user_profile=self.user_profile, name=connection[password]
        )

        # retrieve the proxyUsername Secret, if it exists
        proxy_password_name = self.camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PROXY_PASSWORD.value)
        if connection.get(proxy_password_name):
            connection[proxy_password_name] = self.get_or_create_secret(
                user_profile=self.user_profile,
                name=connection[proxy_password_name],
            )

        return connection

    @property
    def password_secret(self) -> Optional[Secret]:
        """
        Return the password secret for the SQL connection.

        This property retrieves the `Secret` object associated with the password for the current SQL connection,
        either from the manifest or the ORM model. If the secret does not exist, a warning is logged and `None` is returned.

        :returns: The password `Secret` instance, or `None` if not found.

        :raises Secret.DoesNotExist:
            If the password secret cannot be found in the database.

        .. important::

            The password secret is cached after the first lookup for efficiency. If the underlying secret changes,
            you must clear the cache to force a reload.


        .. seealso::

            - :class:`Secret`
            - :meth:`proxy_password_secret`
            - :meth:`manifest`
            - :meth:`connection`

        **Example Usage:**

            .. code-block:: python

                secret = broker.password_secret
                if secret:
                    print(secret.value)
                else:
                    print("Password secret not found.")

        """
        if self._password_secret:
            return self._password_secret
        try:
            name = (
                self.manifest.spec.connection.password
                if self.manifest
                else self.connection.password.name if self.connection else None
            )
            self._password_secret = Secret.objects.get(
                user_profile=self.user_profile,
                name=name,
            )
            return self._password_secret
        except Secret.DoesNotExist:
            logger.warning(
                "%s password Secret %s not found for account %s",
                self.formatted_class_name,
                name or "(name is missing)",
                self.account,
            )
        return None

    @property
    def proxy_password_secret(self) -> Optional[Secret]:
        """
        Return the proxy password secret for the SQL connection.

        This property retrieves the `Secret` object associated with the proxy password for the current SQL connection,
        either from the manifest or the ORM model. If the secret does not exist, a warning is logged and `None` is returned.

        :returns: The proxy password `Secret` instance, or `None` if not found.

        :raises Secret.DoesNotExist:
            If the proxy password secret cannot be found in the database.

        .. important::

            - The proxy password secret is cached after the first lookup for efficiency. If the underlying secret changes, you must clear the cache to force a reload.

            - If the proxy password secret is missing, proxy authentication may fail. Always check for `None` before use.

        .. seealso::

            - :class:`Secret`
            - :meth:`password_secret`
            - :meth:`manifest`
            - :meth:`connection`

        **Example Usage:**

            .. code-block:: python

                proxy_secret = broker.proxy_password_secret
                if proxy_secret:
                    print(proxy_secret.value)
                else:
                    print("Proxy password secret not found.")

        """
        if self._proxy_password_secret:
            return self._proxy_password_secret
        try:
            name = (
                self.manifest.spec.connection.proxyPassword
                if self.manifest
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
    def connection(self) -> Optional[SqlConnection]:
        """
        Return the `SqlConnection` ORM instance for the current manifest and account.

        This property retrieves the Django ORM object representing the SQL connection described by the manifest.
        If the connection does not exist in the database, it will be created from the manifest data (if available).
        The result is cached for efficiency.

        :returns: The `SqlConnection` instance, or `None` if not found and cannot be created.

        :raises SAMConnectionBrokerError:
            If the manifest data is invalid or the ORM object cannot be created.

        .. important::

            - The connection is cached after the first lookup or creation. If the underlying data changes, clear the cache to force a reload.

            - If neither a manifest nor an existing ORM object is available, this property returns `None` and logs an error.

        .. seealso::

            - :class:`SqlConnection`
            - :meth:`manifest`
            - :meth:`password_secret`
            - :meth:`proxy_password_secret`

        **Example Usage:**

            .. code-block:: python

                conn = broker.connection
                if conn:
                    print(conn.connection_string)
                else:
                    print("No connection found or could not be created.")

        """
        if self._connection:
            return self._connection

        try:
            name = self.camel_to_snake(self.name)  # type: ignore
            self._connection = SqlConnection.objects.get(account=self.account, name=name)
        except SqlConnection.DoesNotExist as e:
            logger.warning(
                "%s SqlConnection %s not found for account %s",
                self.formatted_class_name,
                self.name or "(name is missing)",
                self.account or "(account is missing)",
            )
            if self.manifest is None:
                logger.error(
                    "%s manifest is not set, cannot create SqlConnection",
                    self.formatted_class_name,
                )
                return None
            model_dump = self.manifest.spec.connection.model_dump()
            model_dump = self.camel_to_snake(model_dump)
            if not isinstance(model_dump, dict):
                raise SAMConnectionBrokerError(
                    message=f"Invalid connection data: {model_dump}",
                    thing=self.kind,
                    command=SmarterJournalCliCommands.APPLY,
                ) from e
            model_dump[SAMMetadataKeys.ACCOUNT.value] = self.account
            model_dump[SAMMetadataKeys.NAME.value] = self.manifest.metadata.name
            model_dump[SAMMetadataKeys.VERSION.value] = self.manifest.metadata.version
            model_dump[SAMMetadataKeys.DESCRIPTION.value] = self.manifest.metadata.description
            model_dump[SAMSqlConnectionSpecConnectionKeys.PASSWORD.value] = self.password_secret
            model_dump[SAMKeys.KIND.value] = self.kind
            self._connection = SqlConnection(**model_dump)
            self._connection.save()
            self._created = True

        return self._connection

    @property
    def is_valid(self) -> bool:
        """
        Return True if the `SqlConnection` instance exists and is valid.

        This property checks whether the current SQL connection object is present and passes its internal validation logic.
        If the connection does not exist or validation fails, returns False and logs a warning.

        :returns: `True` if the connection exists and is valid, `False` otherwise.

        .. note::

            - returns `False` if no connection is found.
            - If validation fails, a warning is logged with the reason. Check logs for troubleshooting.

        .. seealso::

            - :meth:`connection`
            - :class:`SqlConnection`

        **Example Usage:**

            .. code-block:: python

                if broker.is_valid:
                    print("Connection is valid and ready.")
                else:
                    print("Connection is missing or invalid.")
        """
        if self.connection is None:
            return False
        try:
            return self.connection.validate()
        except Exception as e:
            logger.warning("%s is_valid() failed for %s %s", self.formatted_class_name, self.kind, str(e))
        return False

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the `SqlConnection` model.

        This method generates and returns a sample manifest for a SQL connection, including all required fields
        and example values for supported database engines and authentication methods. The response is formatted
        as a JSON object suitable for use in API documentation, testing, or as a template for user submissions.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: A `SmarterJournaledJsonResponse` containing the example manifest.

        .. seealso::

            - :class:`SAMSqlConnection`
            - :class:`SAMSqlConnectionSpec`
            - :class:`SmarterJournaledJsonResponse`
            - :data:`DbEngines`
            - :data:`DBMSAuthenticationMethods`
            - :class:`SmarterJournalCliCommands`
            - :class:`SAMKeys`
            - :class:`SAMMetadataKeys`
            - :class:`SAMSqlConnectionSpecKeys`
            - :class:`SAMSqlConnectionSpecConnectionKeys`

        **Example Usage:**

            .. code-block:: python

                response = broker.example_manifest(request)
                print(response.data)

        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        choices = ", ".join(DbEngines.all_values())

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "example_connection",
                SAMMetadataKeys.DESCRIPTION.value: f"Example database connection. db_engines: {choices}. authentication methods: {DBMSAuthenticationMethods.all_values()}",
                SAMMetadataKeys.VERSION.value: "0.1.0",
            },
            SAMKeys.SPEC.value: {
                SAMSqlConnectionSpecKeys.CONNECTION.value: {
                    SAMSqlConnectionSpecConnectionKeys.DB_ENGINE.value: DbEngines.MYSQL.value,
                    SAMSqlConnectionSpecConnectionKeys.AUTHENTICATION_METHOD.value: DBMSAuthenticationMethods.TCPIP.value,
                    SAMSqlConnectionSpecConnectionKeys.TIMEOUT.value: 30,
                    SAMSqlConnectionSpecConnectionKeys.DESCRIPTION.value: "example database connection",
                    SAMSqlConnectionSpecConnectionKeys.USE_SSL.value: False,
                    SAMSqlConnectionSpecConnectionKeys.SSL_CERT.value: "",
                    SAMSqlConnectionSpecConnectionKeys.SSL_KEY.value: "",
                    SAMSqlConnectionSpecConnectionKeys.SSL_CA.value: "",
                    SAMSqlConnectionSpecConnectionKeys.HOSTNAME.value: "localhost",
                    SAMSqlConnectionSpecConnectionKeys.PORT.value: 3306,
                    SAMSqlConnectionSpecConnectionKeys.DATABASE.value: "example_db",
                    SAMSqlConnectionSpecConnectionKeys.USERNAME.value: "example_user",
                    SAMSqlConnectionSpecConnectionKeys.PASSWORD.value: "example_password",
                    SAMSqlConnectionSpecConnectionKeys.POOL_SIZE.value: 5,
                    SAMSqlConnectionSpecConnectionKeys.MAX_OVERFLOW.value: 10,
                    SAMSqlConnectionSpecConnectionKeys.PROXY_PROTOCOL.value: "https",
                    SAMSqlConnectionSpecConnectionKeys.PROXY_HOST.value: "proxy.example.com",
                    SAMSqlConnectionSpecConnectionKeys.PROXY_PORT.value: 8080,
                    SAMSqlConnectionSpecConnectionKeys.PROXY_USERNAME.value: "proxy_user",
                    SAMSqlConnectionSpecConnectionKeys.PROXY_PASSWORD.value: "proxy_password",
                    SAMSqlConnectionSpecConnectionKeys.SSH_KNOWN_HOSTS.value: "",
                }
            },
        }
        pydantic_model = self.pydantic_model(**data)
        data = json.loads(pydantic_model.model_dump_json())
        return self.json_response_ok(command=command, data=data)

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve SqlConnection manifests based on search criteria.
        This method fetches SqlConnection objects from the database that match the provided
        search parameters (e.g., name) and returns their serialized representations in a JSON response.

        :raises SAMBrokerErrorNotReady:
            If the required parameters (e.g., name) are not provided.
        :raises SAMConnectionBrokerError:
            If there is an error during data retrieval or serialization.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments for search criteria (e.g., name).
        :returns: A `SmarterJournaledJsonResponse` containing the serialized SqlConnection data

        .. seealso::

            - :class:`SqlConnection`
            - :class:`SqlConnectionSerializer`
            - :class:`SmarterJournaledJsonResponse`
            - :class:`SmarterJournalCliCommands`
            - :class:`SAMKeys`
            - :class:`SAMMetadataKeys`
            - :class:`SCLIResponseGet`
            - :class:`SCLIResponseGetData`
        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name: Optional[str] = kwargs.get(SAMMetadataKeys.NAME.value)
        name = name or self.name
        if name is None:
            raise SAMBrokerErrorNotReady(
                message="Name parameter is required",
                thing=self.kind,
                command=command,
            )
        data = []

        # generate a QuerySet of SqlConnection objects that match our search criteria
        if name:
            sql_connections = SqlConnection.objects.filter(account=self.account, name=name)
        else:
            sql_connections = SqlConnection.objects.filter(account=self.account)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each SqlConnection
        for sql_connection in sql_connections:
            try:
                model_dump = self.serializer(sql_connection).data
                if not model_dump:
                    raise SAMConnectionBrokerError(
                        f"Model dump failed for {self.kind} {sql_connection.name}", thing=self.kind, command=command
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
        Apply the manifest: copy manifest data to the Django ORM model and save to the database.

        This method loads and validates the manifest, transforms it into a Django ORM model dictionary,
        and updates or creates the corresponding `SqlConnection` object in the database. Read-only fields
        (such as ``id``, ``created_at``, ``updated_at``) are excluded from updates. Calls the base class
        ``apply()`` to ensure manifest validation before proceeding.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: A `SmarterJournaledJsonResponse` with the result of the apply operation.

        :raises SAMBrokerErrorNotReady:
            If no connection is found or required data is missing.
        :raises SAMConnectionBrokerError:
            If saving the model fails or data is invalid.

        .. seealso::

            - :meth:`manifest_to_django_orm`
            - :class:`SqlConnection`
            - :class:`SmarterJournaledJsonResponse`
            - :class:`SmarterJournalCliCommands`
            - :class:`SAMKeys`
            - :class:`SAMMetadataKeys`
            - :class:`SAMSqlConnectionSpecConnectionKeys`

        **Example Usage:**

            .. code-block:: python

                response = broker.apply(request)
                print(response.data)

        """
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        readonly_fields = ["id", "created_at", "updated_at"]

        if self.connection is None:
            raise SAMBrokerErrorNotReady(
                message="No connection found. Cannot apply manifest.",
                thing=self.kind,
                command=command,
            )
        try:
            password_name = self.camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PASSWORD.value)
            proxy_password_name = self.camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PROXY_PASSWORD.value)
            data = self.manifest_to_django_orm()

            for field in readonly_fields:
                data.pop(field, None)
            for key, value in data.items():
                if key == password_name:
                    setattr(self.connection, key, self.password_secret)
                elif key == proxy_password_name:
                    setattr(self.connection, key, self.proxy_password_secret)
                else:
                    setattr(self.connection, key, value)
            self.connection.save()
        except Exception as e:
            raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response for chat interactions.
        This is not implemented for SQL connections.

        :raises SAMBrokerErrorNotImplemented:
            Always, as chat functionality is not supported for SQL connections.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: Never returns; always raises an error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response with the manifest data for the current SQL connection.

        This method retrieves the current `SqlConnection` ORM instance, serializes its data (including metadata and status),
        and returns a structured JSON response suitable for API consumers or UI display. It also includes connection status
        such as the connection string and validation result.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (e.g., name).
        :returns: A `SmarterJournaledJsonResponse` containing the manifest and connection status.

        :raises SAMBrokerErrorNotReady:
            If the user is not authenticated or the connection cannot be found.
        :raises SAMConnectionBrokerError:
            If serialization or data transformation fails.

        .. seealso::

            - :class:`SqlConnection`
            - :class:`SAMSqlConnection`
            - :class:`SmarterJournaledJsonResponse`
            - :class:`SAMKeys`
            - :class:`SAMMetadataKeys`
            - :class:`SAMSqlConnectionStatusKeys`

        **Example Usage:**

            .. code-block:: python

                response = broker.describe(request, name="my_connection")
                print(response.data)

        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command, *args, **kwargs)
        if self.user is None or not self.user.is_authenticated:
            raise SAMBrokerErrorNotReady(
                message="User is not authenticated or is not set. Cannot describe.",
                thing=self.kind,
                command=command,
            )

        if self.connection is None:
            raise SAMBrokerErrorNotReady(
                message="No connection found. Cannot describe.",
                thing=self.kind,
                command=command,
            )
        try:
            data = model_to_dict(self.connection)
            data = self.snake_to_camel(data)
            if not isinstance(data, dict):
                raise SAMConnectionBrokerError(
                    message=f"Invalid connection data: {data}",
                    thing=self.kind,
                    command=command,
                )
            data.pop("id")
            data.pop(SAMMetadataKeys.NAME.value)
            data[SAMMetadataKeys.ACCOUNT.value] = self.connection.account.account_number

            # swap out the password and proxy password secrets instance references for their str names
            data[self.camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PASSWORD.value)] = (
                self.password_secret.name if self.password_secret else None
            )
            data[self.camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PROXY_PASSWORD.value)] = (
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
                SAMKeys.SPEC.value: {SAMSqlConnectionSpecKeys.CONNECTION.value: data},
                SAMKeys.STATUS.value: {
                    SAMSqlConnectionStatusKeys.CONNECTION_STRING.value: self.connection.connection_string,
                    SAMSqlConnectionStatusKeys.IS_VALID.value: self.is_valid,
                },
            }
            pydantic_model = self.pydantic_model(**retval)
            data = pydantic_model.model_dump_json()
            return self.json_response_ok(command=command, data=retval)
        except Exception as e:
            raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the current SQL connection from the database.

        This method removes the `SqlConnection` ORM instance associated with the current manifest and account.
        If the connection exists, it is deleted from the database and a success response is returned. If no connection
        is found, an error is raised.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: A `SmarterJournaledJsonResponse` indicating the result of the delete operation.

        :raises SAMBrokerErrorNotReady:
            If no connection is found to delete.
        :raises SAMConnectionBrokerError:
            If an error occurs during deletion.

        .. seealso::

            - :meth:`connection`
            - :class:`SqlConnection`
            - :class:`SmarterJournaledJsonResponse`

        **Example Usage:**

            .. code-block:: python

                response = broker.delete(request)
                if response.status == "ok":
                    print("Connection deleted successfully.")
                else:
                    print("Delete failed:", response.data)

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
        Deploy the SQL connection.
        This is not implemented for SQL connections.

        :raises SAMBrokerErrorNotImplemented:
            Always, as deploy functionality is not supported for SQL connections.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: Never returns; always raises an error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the SQL connection.
        This is not implemented for SQL connections.

        :raises SAMBrokerErrorNotImplemented:
            Always, as undeploy functionality is not supported for SQL connections.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: Never returns; always raises an error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs for the SQL connection.
        This is not implemented for SQL connections.

        :raises SAMBrokerErrorNotImplemented:
            Always, as log retrieval is not supported for SQL connections.

        :param request: The Django HTTP request object.
        :type request: HttpRequest
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: Never returns; always raises an error.
        :rtype: SmarterJournaledJsonResponse
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Logs not implemented", thing=self.kind, command=command)
