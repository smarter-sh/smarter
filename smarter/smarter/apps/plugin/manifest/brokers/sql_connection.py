# pylint: disable=W0718
"""Smarter API Plugin Manifest handler"""

from typing import Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.mixins import Account, AccountMixin
from smarter.apps.plugin.manifest.models.sql_connection.enum import DbEngines
from smarter.apps.plugin.models import PluginDataSqlConnection
from smarter.apps.plugin.serializers import PluginDataSqlConnectionSerializer
from smarter.common.api import SmarterApiVersions
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
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
from smarter.lib.manifest.loader import SAMLoader

from ..models.sql_connection.const import MANIFEST_KIND
from ..models.sql_connection.model import SAMPluginDataSqlConnection


MAX_RESULTS = 1000


class SAMPluginDataSqlConnectionBrokerError(SAMBrokerError):
    """Base exception for Smarter API Plugin Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API PluginDataSqlConnection Manifest Broker Error"


class SAMPluginDataSqlConnectionBroker(AbstractBroker, AccountMixin):
    """
    Smarter API Plugin Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Plugin manifests
    - using the manifest to initialize the corresponding Pydantic model

    The Plugin object provides the generic services for the Plugin, such as
    instantiation, create, update, delete, etc.
    """

    # override the base abstract manifest model with the Plugin model
    _manifest: SAMPluginDataSqlConnection = None
    _pydantic_model: Type[SAMPluginDataSqlConnection] = SAMPluginDataSqlConnection
    _sql_connection: PluginDataSqlConnection = None

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
    def model_class(self) -> PluginDataSqlConnection:
        return PluginDataSqlConnection

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMPluginDataSqlConnection:
        """
        SAMPluginDataSqlConnection() is a Pydantic model
        that is used to represent the Smarter API Plugin manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader:
            self._manifest = SAMPluginDataSqlConnection(
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
        config_dump["name"] = self.manifest.metadata.name
        config_dump["description"] = self.manifest.metadata.description
        config_dump["version"] = self.manifest.metadata.version
        return config_dump

    @property
    def sql_connection(self) -> PluginDataSqlConnection:
        if self._sql_connection:
            return self._sql_connection

        try:
            self._sql_connection = PluginDataSqlConnection.objects.get(account=self.account, name=self.name)
        except PluginDataSqlConnection.DoesNotExist:
            if self.manifest:
                model_dump = self.manifest.spec.connection.model_dump()
                model_dump["account"] = self.account
                model_dump["name"] = self.manifest.metadata.name
                model_dump["version"] = self.manifest.metadata.version
                model_dump["description"] = self.manifest.metadata.description
                self._sql_connection = PluginDataSqlConnection(**model_dump)
                self._sql_connection.save()

        return self._sql_connection

    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "metadata": {
                "name": "exampleConnection",
                "description": f"points to the Django mysql database. db_engine choices: {DbEngines.all_values()}",
                "version": "0.1.0",
            },
            "spec": {
                "connection": {
                    "db_engine": DbEngines.MYSQL.value,
                    "hostname": "smarter-mysql",
                    "port": 3306,
                    "username": "smarter",
                    "password": "smarter",
                    "database": "smarter",
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

        # generate a QuerySet of PluginDataSqlConnection objects that match our search criteria
        if name:
            sql_connections = PluginDataSqlConnection.objects.filter(account=self.account, name=name)
        else:
            sql_connections = PluginDataSqlConnection.objects.filter(account=self.account)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for sql_connection in sql_connections:
            try:
                model_dump = PluginDataSqlConnectionSerializer(sql_connection).data
                if not model_dump:
                    raise SAMPluginDataSqlConnectionBrokerError(
                        f"Model dump failed for {self.kind} {sql_connection.name}", thing=self.kind, command=command
                    )
                data.append(model_dump)
            except Exception as e:
                raise SAMPluginDataSqlConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMMetadataKeys.NAME.value: name,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=PluginDataSqlConnectionSerializer()),
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
            raise SAMPluginDataSqlConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        return self.json_response_ok(command=command, data={})

    def chat(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """Return a JSON response with the manifest data."""
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.sql_connection:
            try:
                data = model_to_dict(self.sql_connection)
                data.pop("id")
                data.pop("account")
                data.pop("name")
                data.pop("version")
                data.pop("description")
                retval = {
                    "apiVersion": self.api_version,
                    "kind": self.kind,
                    "metadata": {
                        "name": self.sql_connection.name,
                        "description": self.sql_connection.description,
                        "version": self.sql_connection.version,
                    },
                    "spec": {"connection": data},
                    "status": {
                        "connection_string": self.sql_connection.get_connection_string(),
                        "is_valid": self.sql_connection.validate(),
                    },
                }

                return self.json_response_ok(command=command, data=retval)
            except Exception as e:
                raise SAMPluginDataSqlConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="No connection found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.sql_connection:
            try:
                self.sql_connection.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMPluginDataSqlConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
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
