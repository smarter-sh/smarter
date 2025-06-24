# pylint: disable=W0718
"""Smarter Api SqlConnection Manifest handler"""

import json
from logging import getLogger
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
from smarter.common.utils import camel_to_snake
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
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


logger = getLogger(__name__)


class SAMSqlConnectionBroker(SAMConnectionBaseBroker):
    """
    Smarter API SqlConnection Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml SqlConnection manifests
    - using the manifest to initialize the corresponding Pydantic model

    The SqlConnection object provides the generic services for the SqlConnection, such as
    instantiation, create, update, delete, etc.
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
        """Return the serializer for the broker."""
        return SqlConnectionSerializer

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMSqlConnectionBroker()"

    @property
    def model_class(self) -> Type[SqlConnection]:
        return SqlConnection

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSqlConnection]:
        """
        SAMSqlConnection() is a Pydantic model
        that is used to represent the Smarter API SqlConnection manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
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
        Transform the Smarter API User manifest into a Django ORM model.
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
        password = camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PASSWORD.value)
        connection[SAMSqlConnectionSpecConnectionKeys.PASSWORD.value] = self.get_or_create_secret(
            user_profile=self.user_profile, name=connection[password]
        )

        # retrieve the proxyUsername Secret, if it exists
        proxy_password_name = camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PROXY_PASSWORD.value)
        if connection.get(proxy_password_name):
            connection[proxy_password_name] = self.get_or_create_secret(
                user_profile=self.user_profile,
                name=connection[proxy_password_name],
            )

        return connection

    @property
    def password_secret(self) -> Optional[Secret]:
        """
        Return the password secret for the SqlConnection.
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
        Return the proxy password secret for the SqlConnection.
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
        Return True if the SqlConnection instance
        exists and is valid.
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
        Return an example manifest for the SqlConnection model.
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
        apply the manifest. copy the manifest data to the Django ORM model and
        save the model to the database. Call super().apply() to ensure that the
        manifest is loaded and validated before applying the manifest to the
        Django ORM model.
        Note that there are fields included in the manifest that are not editable
        and are therefore removed from the Django ORM model dict prior to attempting
        the save() command. These fields are defined in the readonly_fields list.
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
            password_name = camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PASSWORD.value)
            proxy_password_name = camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PROXY_PASSWORD.value)
            data = self.manifest_to_django_orm()

            logger.info("apply() django model dump: %s", data)

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
        return self.json_response_ok(command=command, data={})

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """Return a JSON response with the manifest data."""
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command, *args, **kwargs)
        if self.user is None or not self.user.is_authenticated:
            raise SAMBrokerErrorNotReady(
                message="User is not authenticated or is not set. Cannot describe.",
                thing=self.kind,
                command=command,
            )

        logger.info(
            "%s.describe() called with request=%s, args=%s, kwargs=%s, user=%s",
            self.formatted_class_name,
            request,
            args,
            kwargs,
            request.user.username if request.user.is_authenticated else "Anonymous",  # type: ignore
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
            data[camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PASSWORD.value)] = (
                self.password_secret.name if self.password_secret else None
            )
            data[camel_to_snake(SAMSqlConnectionSpecConnectionKeys.PROXY_PASSWORD.value)] = (
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
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Logs not implemented", thing=self.kind, command=command)
