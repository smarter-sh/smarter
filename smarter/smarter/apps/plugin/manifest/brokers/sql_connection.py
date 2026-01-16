# pylint: disable=W0718
"""Smarter Api SqlConnection Manifest handler"""

import logging
from datetime import datetime
from typing import TYPE_CHECKING, Optional, Type

from smarter.apps.account.models import Secret
from smarter.apps.plugin.manifest.enum import (
    SAMSqlConnectionSpecConnectionKeys,
)
from smarter.apps.plugin.manifest.models.common.connection.metadata import (
    SAMConnectionCommonMetadata,
)
from smarter.apps.plugin.manifest.models.common.connection.status import (
    SAMConnectionCommonStatus,
)
from smarter.apps.plugin.manifest.models.sql_connection.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.sql_connection.enum import (
    DbEngines,
    DBMSAuthenticationMethods,
)
from smarter.apps.plugin.manifest.models.sql_connection.model import SAMSqlConnection
from smarter.apps.plugin.manifest.models.sql_connection.spec import (
    Connection as PydanticSqlConnection,
)
from smarter.apps.plugin.manifest.models.sql_connection.spec import (
    SAMSqlConnectionSpec,
)
from smarter.apps.plugin.models import SqlConnection
from smarter.apps.plugin.serializers import SqlConnectionSerializer
from smarter.lib import json
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
from smarter.lib.manifest.broker import (
    SAMBrokerError,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)

from . import SAMConnectionBrokerError
from .connection_base import SAMConnectionBaseBroker


if TYPE_CHECKING:
    from django.http import HttpRequest


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.PLUGIN_LOGGING) or waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SAMSqlConnectionBroker(SAMConnectionBaseBroker):
    """
    Broker for Smarter API SQL Connection manifests.

    This class is responsible for loading, validating, and parsing Smarter API YAML SqlConnection manifests,
    and initializing the corresponding Pydantic model. It provides generic services for SQL connections,
    such as instantiation, creation, update, and deletion.

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

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        if not self.ready:
            if not self.loader and not self.manifest and not self.connection:
                logger.error(
                    "%s.__init__() No loader nor existing Connection provided for %s broker. Cannot initialize.",
                    self.formatted_class_name,
                    self.kind,
                )
                return
            if self.loader and self.loader.manifest_kind != self.kind:
                raise SAMBrokerErrorNotReady(
                    f"Loader manifest kind {self.loader.manifest_kind} does not match broker kind {self.kind}",
                    thing=self.kind,
                )

            if self.loader:
                self._manifest = SAMSqlConnection(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                    spec=SAMSqlConnectionSpec(**self.loader.manifest_spec),
                )
            if self._manifest:
                logger.info(
                    "%s.__init__() initialized manifest from loader for %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.manifest.metadata.name,
                )
        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        if self.ready:
            logger.info(msg)
        else:
            logger.warning(msg)

    # override the base abstract manifest model with the SqlConnection model
    _manifest: Optional[SAMSqlConnection] = None
    _pydantic_model: Type[SAMSqlConnection] = SAMSqlConnection
    _connection: Optional[SqlConnection] = None
    _password_secret: Optional[Secret] = None
    _proxy_password_secret: Optional[Secret] = None

    def connection_init(self) -> None:
        """
        Initialize or reset the connection and related cached properties.

        This method clears the cached `SqlConnection` instance and associated secrets,
        allowing for re-initialization or reloading of the connection data.

        **Example Usage:**

            .. code-block:: python

                broker.connection_init()
                connection = broker.connection  # Re-initialized connection

        """
        super().connection_init()
        self._manifest = None
        self._connection = None
        self._password_secret = None
        self._proxy_password_secret = None

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def SerializerClass(self) -> Type[SqlConnectionSerializer]:
        """
        Returns the SerializerClass class used by the broker for SQL connection objects.

        This property provides the appropriate SerializerClass for converting `SqlConnection` ORM instances
        to and from Python data structures, typically for API responses or internal processing.

        :returns: The SerializerClass class (`SqlConnectionSerializer`) for SQL connection objects.

        .. seealso::

            - :class:`SqlConnectionSerializer`
            - :class:`SqlConnection`

        **Example Usage:**

            .. code-block:: python

                serializer_cls = broker.SerializerClass
                SerializerClass = serializer_cls(sql_connection_instance)
                data = SerializerClass.data

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
        return f"{__name__}.{self.__class__.__name__}[{id(self)}]"

    @property
    def ORMModelClass(self) -> Type[SqlConnection]:
        """
        Returns the Django ORM model class associated with this broker.

        This property provides the concrete model used for SQL connection objects in the database.
        It is essential for operations that require direct interaction with the ORM, such as queries,
        creation, updates, and deletions.

        :returns: The Django model class (`SqlConnection`) for SQL connection records.


        .. seealso::

            - :class:`SqlConnection`
            - :meth:`SerializerClass`

        **Example Usage:**

            .. code-block:: python

                model_cls = broker.ORMModelClass
                queryset = model_cls.objects.filter(account=account)


        """
        return SqlConnection

    @property
    def SAMModelClass(self) -> Type[SAMSqlConnection]:
        """
        Return the Pydantic model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[SAMSqlConnection]
        """
        return SAMSqlConnection

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
            if not isinstance(self._manifest, SAMSqlConnection):
                raise SAMConnectionBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        logger.debug(
            "%s.manifest property called for %s %s %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
        )

        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMSqlConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMConnectionCommonMetadata(**self.loader.manifest_metadata),
                spec=SAMSqlConnectionSpec(**self.loader.manifest_spec),
            )
        # 2.) next, (and only if a loader is not available) try to initialize
        #     from existing Account model if available
        elif self._connection:
            metadata = self.sam_connection_metadata()
            if not metadata:
                raise SAMBrokerErrorNotImplemented(
                    f"{self.formatted_class_name} manifest cannot be constructed without connection metadata.",
                    thing=self.kind,
                    command=SmarterJournalCliCommands.APPLY,
                )
            status = self.sam_connection_status()
            if not status:
                raise SAMBrokerErrorNotImplemented(
                    f"{self.formatted_class_name} manifest cannot be constructed without connection status.",
                    thing=self.kind,
                    command=SmarterJournalCliCommands.APPLY,
                )
            spec = SAMSqlConnectionSpec(
                connection=PydanticSqlConnection(
                    dbEngine=self.connection.db_engine,
                    hostname=self.connection.hostname,
                    port=self.connection.port,
                    database=self.connection.database,
                    username=self.connection.username,
                    password=self.connection.password.get_secret() if self.connection.password else None,
                    timeout=self.connection.timeout,
                    useSsl=self.connection.use_ssl,
                    sslCert=self.connection.ssl_cert,
                    sslKey=self.connection.ssl_key,
                    sslCa=self.connection.ssl_ca,
                    proxyHost=self.connection.proxy_host,
                    proxyPort=self.connection.proxy_port,
                    proxyUsername=self.connection.proxy_username,
                    proxyPassword=(
                        self.connection.proxy_password.get_secret() if self.connection.proxy_password else None
                    ),
                    sshKnownHosts=self.connection.ssh_known_hosts,
                    poolSize=self.connection.pool_size,
                    maxOverflow=self.connection.max_overflow,
                    authenticationMethod=self.connection.authentication_method,
                )
            )

            self._manifest = SAMSqlConnection(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=spec,
                status=status,
            )
            return self._manifest
        else:
            logger.warning("%s.manifest could not be initialized", self.formatted_class_name)
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
        logger.debug(
            "%s.manifest_to_django_orm() called for %s %s %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
        )
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
            logger.debug(
                "%s.manifest_to_django_orm() recasting connection: %s (%s)",
                self.formatted_class_name,
                connection,
                type(connection),
            )
            connection = json.loads(json.dumps(connection))
        connection[SAMMetadataKeys.NAME.value] = self.manifest.metadata.name
        connection[SAMMetadataKeys.DESCRIPTION.value] = self.manifest.metadata.description
        connection[SAMMetadataKeys.VERSION.value] = self.manifest.metadata.version
        connection[SAMKeys.KIND.value] = self.kind

        # retrieve the password Secret
        password = self.camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PASSWORD.value)
        try:
            connection[SAMSqlConnectionSpecConnectionKeys.PASSWORD.value] = self.get_or_create_secret(
                user_profile=self.user_profile, name=connection[password]
            )
        except SAMBrokerError as e:
            raise SAMConnectionBrokerError(
                message=f"Failed to create or retrieve {Secret.__name__} {connection[password]}",
                thing=self.thing,
            ) from e
        except Exception as e:
            raise SAMConnectionBrokerError(
                message=f"Encountered an unexpected error while creating or retrieving {Secret.__name__} {connection[password]}",
                thing=self.thing,
            ) from e

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
                "%s password Secret %s not found for %s",
                self.formatted_class_name,
                name or "(name is missing)",
                self.user_profile,
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
                "%s proxy password Secret %s not found for %s",
                self.formatted_class_name,
                name or "(name is missing)",
                self.user_profile,
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
        except SqlConnection.DoesNotExist:
            logger.warning(
                "%s SqlConnection %s not found for account %s",
                self.formatted_class_name,
                self.name or "(name is missing)",
                self.user_profile or "(user_profile is missing)",
            )
            if self._manifest is None:
                logger.error(
                    "%s manifest is not set, cannot create SqlConnection",
                    self.formatted_class_name,
                )
                return None
            model_dump = self._manifest.spec.connection.model_dump()
            model_dump = self.camel_to_snake(model_dump)
            if not isinstance(model_dump, dict):
                model_dump = json.loads(json.dumps(model_dump))
            model_dump[SAMMetadataKeys.ACCOUNT.value] = self.account
            model_dump[SAMMetadataKeys.NAME.value] = self.manifest.metadata.name
            model_dump[SAMMetadataKeys.VERSION.value] = self.manifest.metadata.version
            model_dump[SAMMetadataKeys.DESCRIPTION.value] = self.manifest.metadata.description
            model_dump[SAMSqlConnectionSpecConnectionKeys.PASSWORD.value] = self.password_secret
            model_dump[SAMKeys.KIND.value] = self.kind
            self._connection = SqlConnection(**model_dump)

            logger.info(
                "%s creating SqlConnection %s for account %s: %s",
                self.formatted_class_name,
                self.name,
                self.account,
                model_dump,
            )

            self._connection.save()
            self._created = True
            logger.info(
                "%s created SqlConnection %s for account %s",
                self.formatted_class_name,
                self.name or "(name is missing)",
                self.account or "(account is missing)",
            )

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
            logger.warning(
                "%s is_valid() failed: connection is None for %s %s",
                self.formatted_class_name,
                self.kind,
                self.name or "(name is missing)",
            )
            return False
        try:
            if self.connection.validate():
                logger.info(
                    "%s is_valid() succeeded for %s %s",
                    self.formatted_class_name,
                    self.kind,
                    self.name or "(name is missing)",
                )
                if self.manifest is not None:
                    return True
                logger.warning(
                    "%s is_valid() failed for %s %s: manifest is missing",
                    self.formatted_class_name,
                    self.kind,
                    self.name or "(name is missing)",
                )

        except Exception as e:
            logger.warning("%s is_valid() failed for %s %s", self.formatted_class_name, self.kind, str(e))
        return False

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################

    def example_manifest(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return an example manifest for the `SqlConnection` model.

        This method generates and returns a sample manifest for a SQL connection, including all required fields
        and example values for supported database engines and authentication methods. The response is formatted
        as a JSON object suitable for use in API documentation, testing, or as a template for user submissions.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
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

        **Example Usage:**

            .. code-block:: python

                response = broker.example_manifest(request)
                print(response.data)

        """
        logger.debug(
            "%s.example_manifest() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)

        metadata = SAMConnectionCommonMetadata(
            name="example_connection",
            description="Example database connection",
            version="0.1.0",
            tags=["example", "sql", "connection"],
            annotations=[
                {"smarter.sh/plugin": "example_plugin"},
                {"smarter.sh/created_by": "smarter_sql_connection_broker"},
            ],
        )
        connection = PydanticSqlConnection(
            dbEngine=DbEngines.MYSQL.value,
            hostname="localhost",
            port=3306,
            database="example_db",
            username="example_user",
            password="example_password",
            timeout=30,
            useSsl=False,
            sslCert="",
            sslKey=None,
            sslCa=None,
            proxyHost=None,
            proxyPort=None,
            proxyUsername=None,
            proxyPassword=None,
            sshKnownHosts=None,
            poolSize=5,
            maxOverflow=10,
            authenticationMethod=DBMSAuthenticationMethods.TCPIP.value,
        )
        spec = SAMSqlConnectionSpec(connection=connection)
        status = SAMConnectionCommonStatus(
            account_number="123456789012",
            username="example_user",
            created=datetime(2024, 1, 1, 0, 0, 0),
            modified=datetime(2024, 1, 1, 0, 0, 0),
        )
        sam_sql_connection = SAMSqlConnection(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=metadata,
            spec=spec,
            status=status,
        )

        data = json.loads(sam_sql_connection.model_dump_json())
        return self.json_response_ok(command=command, data=data)

    def get(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve SqlConnection manifests based on search criteria.
        This method fetches SqlConnection objects from the database that match the provided
        search parameters (e.g., name) and returns their serialized representations in a JSON response.

        :raises SAMBrokerErrorNotReady:
            If the required parameters (e.g., name) are not provided.
        :raises SAMConnectionBrokerError:
            If there is an error during data retrieval or serialization.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
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
        logger.debug(
            "%s.get() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
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

        model_titles = self.get_model_titles(serializer=self.SerializerClass())

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each SqlConnection
        for sql_connection in sql_connections:
            try:
                self.connection_init()
                self._connection = sql_connection

                model_dump = self.SerializerClass(sql_connection).data
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)

            except Exception as e:
                raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: model_titles,
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest: copy manifest data to the Django ORM model and save to the database.

        This method loads and validates the manifest, transforms it into a Django ORM model dictionary,
        and updates or creates the corresponding `SqlConnection` object in the database. Read-only fields
        (such as ``id``, ``created_at``, ``updated_at``) are excluded from updates. Calls the base class
        ``apply()`` to ensure manifest validation before proceeding.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
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
        logger.debug(
            "%s.apply() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
        super().apply(request, args, kwargs)
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

    def chat(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response for chat interactions.
        This is not implemented for SQL connections.

        :raises SAMBrokerErrorNotImplemented:
            Always, as chat functionality is not supported for SQL connections.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: Never returns; always raises an error.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.chat() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return a JSON response with the manifest data for the current SQL connection.

        This method retrieves the current `SqlConnection` ORM instance, serializes its data (including metadata and status),
        and returns a structured JSON response suitable for API consumers or UI display. It also includes connection status
        such as the connection string and validation result.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
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
        logger.debug(
            "%s.describe() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command, *args, **kwargs)
        if self.user is None or not self.user.is_authenticated:
            raise SAMBrokerErrorNotReady(
                message="User is not authenticated or is not set. Cannot describe.",
                thing=self.kind,
                command=command,
            )

        if self.manifest is None:
            raise SAMBrokerErrorNotReady(
                message="Manifest is not set. Cannot describe.",
                thing=self.kind,
                command=command,
            )

        model = self.manifest.model_dump()
        return self.json_response_ok(command=command, data=model)

    def delete(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the current SQL connection from the database.

        This method removes the `SqlConnection` ORM instance associated with the current manifest and account.
        If the connection exists, it is deleted from the database and a success response is returned. If no connection
        is found, an error is raised.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
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
        logger.debug(
            "%s.delete() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.connection:
            try:
                self.connection.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="No connection found", thing=self.kind, command=command)

    def deploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deploy the SQL connection.
        This is not implemented for SQL connections.

        :raises SAMBrokerErrorNotImplemented:
            Always, as deploy functionality is not supported for SQL connections.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: Never returns; always raises an error.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.deploy() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the SQL connection.
        This is not implemented for SQL connections.

        :raises SAMBrokerErrorNotImplemented:
            Always, as undeploy functionality is not supported for SQL connections.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: Never returns; always raises an error.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.undeploy() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs for the SQL connection.
        This is not implemented for SQL connections.

        :raises SAMBrokerErrorNotImplemented:
            Always, as log retrieval is not supported for SQL connections.

        :param request: The Django HTTP request object.
        :type request: "HttpRequest"
        :param args: Additional positional arguments (unused).
        :param kwargs: Additional keyword arguments (unused).
        :returns: Never returns; always raises an error.
        :rtype: SmarterJournaledJsonResponse
        """
        logger.debug(
            "%s.logs() called for %s %s %s args: %s kwargs: %s",
            self.formatted_class_name,
            self.kind,
            self.name,
            self.user_profile,
            args,
            kwargs,
        )
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Logs not implemented", thing=self.kind, command=command)
