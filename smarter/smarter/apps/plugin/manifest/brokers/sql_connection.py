# pylint: disable=W0718
"""Smarter API Plugin Manifest handler"""

from django.forms.models import model_to_dict
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.mixins import Account, AccountMixin, UserProfile
from smarter.apps.plugin.models import PluginDataSqlConnection
from smarter.lib.django.user import UserType
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.enum import SAMApiVersions
from smarter.lib.manifest.exceptions import SAMExceptionBase
from smarter.lib.manifest.loader import SAMLoader

from ..models.sql_connection.const import MANIFEST_KIND
from ..models.sql_connection.model import SAMPluginDataSqlConnection


MAX_RESULTS = 1000


class SAMPluginDataSqlConnectionBrokerError(SAMExceptionBase):
    """Base exception for Smarter API Plugin Broker handling."""


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
    _sql_connection: PluginDataSqlConnection = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        api_version: str = SAMApiVersions.V1.value,
        account: Account = None,
        user: UserType = None,
        user_profile: UserProfile = None,
        name: str = None,
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
        self._account = account
        self._user = user
        self._user_profile = user_profile
        super().__init__(
            account=self.account,
            api_version=api_version,
            name=name,
            kind=MANIFEST_KIND,
            loader=loader,
            manifest=manifest,
            file_path=file_path,
            url=url,
        )

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
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

    @property
    def sql_connection(self) -> PluginDataSqlConnection:
        if not self._sql_connection:
            try:
                self._sql_connection = PluginDataSqlConnection.objects.get(
                    account=self.account, name=self.manifest.metadata.name
                )
            except PluginDataSqlConnection.DoesNotExist:
                model_dump = self.manifest.spec.connection.model_dump()
                model_dump["account"] = self.account
                model_dump["name"] = self.manifest.metadata.name
                model_dump["version"] = self.manifest.metadata.version
                model_dump["description"] = self.manifest.metadata.description
                self._sql_connection = PluginDataSqlConnection(**model_dump)
                self._sql_connection.save()

        return self._sql_connection

    def example_manifest(self, request: HttpRequest = None) -> JsonResponse:
        data = {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "metadata": {
                "name": "exampleConnection",
                "description": "points to the Django mysql database",
                "version": "0.1.0",
            },
            "spec": {
                "connection": {
                    "db_engine": "django.db.backends.mysql",
                    "hostname": "smarter-mysql",
                    "port": 3306,
                    "username": "smarter",
                    "password": "smarter",
                    "database": "smarter",
                }
            },
        }
        return self.success_response(operation=self.get.__name__, data=data)

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    def get(
        self, request: HttpRequest = None, name: str = None, all_objects: bool = False, tags: str = None
    ) -> JsonResponse:

        data = []

        # generate a QuerySet of PluginDataSqlConnection objects that match our search criteria
        if name:
            sql_connections = PluginDataSqlConnection.objects.filter(account=self.account, name=name)
        else:
            sql_connections = PluginDataSqlConnection.objects.filter(account=self.account)

        if not sql_connections.exists():
            return self.not_found_response()

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for sql_connection in sql_connections:
            try:
                model_dump = model_to_dict(sql_connection)
                if not model_dump:
                    raise SAMPluginDataSqlConnectionBrokerError(
                        f"Model dump failed for {self.kind} {sql_connection.name}"
                    )
                data.append(model_dump)
            except Exception as e:
                return self.err_response(self.get.__name__, e)
        data = {
            "apiVersion": self.api_version,
            "kind": self.kind,
            "name": name,
            "all_objects": all_objects,
            "tags": tags,
            "metadata": {"count": len(data)},
            "items": data,
        }
        return self.success_response(operation=self.get.__name__, data=data)

    def apply(self, request: HttpRequest = None) -> JsonResponse:
        try:
            self.sql_connection.save()
        except Exception as e:
            return self.err_response("create", e)
        return self.success_response(operation=self.apply.__name__, data={})

    def describe(self, request: HttpRequest = None) -> JsonResponse:
        """Return a JSON response with the manifest data."""
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

                return self.success_response(operation=self.describe.__name__, data=retval)
            except Exception as e:
                return self.err_response(self.describe.__name__, e)
        return self.not_ready_response()

    def delete(self, request: HttpRequest = None) -> JsonResponse:
        if self.sql_connection:
            try:
                self.sql_connection.delete()
                return self.success_response(operation=self.delete.__name__, data={})
            except Exception as e:
                return self.err_response(self.delete.__name__, e)
        return self.not_ready_response()

    def deploy(self, request: HttpRequest = None) -> JsonResponse:
        return self.not_implemented_response()

    def logs(self, request: HttpRequest = None) -> JsonResponse:
        return self.not_implemented_response()
