# pylint: disable=W0718
"""Smarter Api SqlConnection Manifest handler"""

from typing import Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.mixins import Account, AccountMixin
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
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)
from smarter.lib.manifest.loader import SAMLoader

from ..models.sql_connection.const import MANIFEST_KIND
from ..models.sql_connection.model import SAMSqlConnection
from . import SAMConnectionBrokerError


class SAMSqlConnectionBroker(AbstractBroker, AccountMixin):
    """
    Smarter API SqlConnection Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml SqlConnection manifests
    - using the manifest to initialize the corresponding Pydantic model

    The SqlConnection object provides the generic services for the SqlConnection, such as
    instantiation, create, update, delete, etc.
    """

    # override the base abstract manifest model with the SqlConnection model
    _manifest: SAMSqlConnection = None
    _pydantic_model: Type[SAMSqlConnection] = SAMSqlConnection
    _sql_connection: SqlConnection = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: HttpRequest,
        account: Account,
        api_version: str = SmarterApiVersions.V1,
        name: str = None,
        kind: str = None,
        loader: SAMLoader = None,
        manifest: str = None,
        file_path: str = None,
        url: str = None,
    ):
        """
        Load, validate and parse the manifest. The parent will initialize
        the generic manifest loader class, SAMLoader(), which can then be used to
        provide initialization data to any kind of manifest model. the loader
        also performs cursory high-level validation of the manifest, sufficient
        to ensure that the manifest is a valid yaml file and that it contains
        the required top-level keys.
        """
        super().__init__(
            request=request,
            api_version=api_version,
            account=account,
            name=name,
            kind=kind,
            loader=loader,
            manifest=manifest,
            file_path=file_path,
            url=url,
        )

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def model_class(self) -> SqlConnection:
        return SqlConnection

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMSqlConnection:
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
        if self.loader:
            self._manifest = SAMSqlConnection(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=self.loader.manifest_metadata,
                spec=self.loader.manifest_spec,
                status=self.loader.manifest_status,
            )
        return self._manifest

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API User manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.connection.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        config_dump[SAMMetadataKeys.NAME] = self.manifest.metadata.name
        config_dump[SAMMetadataKeys.DESCRIPTION] = self.manifest.metadata.description
        config_dump[SAMMetadataKeys.VERSION] = self.manifest.metadata.version
        return config_dump

    @property
    def sql_connection(self) -> SqlConnection:
        if self._sql_connection:
            return self._sql_connection

        try:
            self._sql_connection = SqlConnection.objects.get(account=self.account, name=self.name)
        except SqlConnection.DoesNotExist:
            if self.manifest:
                model_dump = self.manifest.spec.connection.model_dump()
                model_dump[SAMMetadataKeys.ACCOUNT] = self.account
                model_dump[SAMMetadataKeys.NAME] = self.manifest.metadata.name
                model_dump[SAMMetadataKeys.VERSION] = self.manifest.metadata.version
                model_dump[SAMMetadataKeys.DESCRIPTION] = self.manifest.metadata.description
                self._sql_connection = SqlConnection(**model_dump)
                self._sql_connection.save()

        return self._sql_connection

    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
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
                SAMMetadataKeys.NAME.value: "exampleConnection",
                SAMMetadataKeys.DESCRIPTION.value: f"Example database connection. db_engines: {choices}. authentication methods: {DBMSAuthenticationMethods.all_values()}",
                SAMMetadataKeys.VERSION.value: "0.1.0",
            },
            SAMKeys.SPEC.value: {
                SAMSqlConnectionSpecKeys.CONNECTION.value: {
                    SAMSqlConnectionSpecConnectionKeys.DB_ENGINE.value: DbEngines.MYSQL.value,
                    SAMSqlConnectionSpecConnectionKeys.AUTHENTICATION_METHOD.value: DBMSAuthenticationMethods.TCPIP.value,
                    SAMSqlConnectionSpecConnectionKeys.TIMEOUT.value: 30,
                    SAMSqlConnectionSpecConnectionKeys.ACCOUNT.value: self.account.account_number,
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
        return self.json_response_ok(command=command, data=data)

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name: str = kwargs.get("name", None)
        data = []

        # generate a QuerySet of SqlConnection objects that match our search criteria
        if name:
            sql_connections = SqlConnection.objects.filter(account=self.account, name=name)
        else:
            sql_connections = SqlConnection.objects.filter(account=self.account)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each SqlConnection
        for sql_connection in sql_connections:
            try:
                model_dump = SqlConnectionSerializer(sql_connection).data
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
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=SqlConnectionSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
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
        try:
            data = self.manifest_to_django_orm()
            for field in readonly_fields:
                data.pop(field, None)
            for key, value in data.items():
                setattr(self.sql_connection, key, value)
            self.sql_connection.save()
        except Exception as e:
            raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        return self.json_response_ok(command=command, data={})

    def chat(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """Return a JSON response with the manifest data."""
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        is_valid = False
        try:
            is_valid = self.sql_connection.validate()
        except Exception:
            pass

        if self.sql_connection:
            try:
                data = model_to_dict(self.sql_connection)
                data.pop("id")
                data.pop(SAMMetadataKeys.ACCOUNT)
                data.pop(SAMMetadataKeys.NAME)
                data.pop(SAMMetadataKeys.DESCRIPTION)
                data.pop(SAMMetadataKeys.VERSION)
                retval = {
                    SAMKeys.APIVERSION: self.api_version,
                    SAMKeys.KIND: self.kind,
                    SAMKeys.METADATA: {
                        SAMMetadataKeys.NAME: self.sql_connection.name,
                        SAMMetadataKeys.DESCRIPTION: self.sql_connection.description,
                        SAMMetadataKeys.VERSION: self.sql_connection.version,
                    },
                    SAMKeys.SPEC: {SAMSqlConnectionSpecKeys.CONNECTION: data},
                    SAMKeys.STATUS: {
                        SAMSqlConnectionStatusKeys.CONNECTION_STRING: self.sql_connection.get_connection_string(),
                        SAMSqlConnectionStatusKeys.IS_VALID: is_valid,
                    },
                }

                return self.json_response_ok(command=command, data=retval)
            except Exception as e:
                raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="No connection found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.sql_connection:
            try:
                self.sql_connection.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="No connection found", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Deploy not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Undeploy not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Logs not implemented", thing=self.kind, command=command)
