# pylint: disable=W0718
"""Smarter Api ApiConnection Manifest handler"""

import json
from logging import getLogger
from typing import Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.mixins import Account, AccountMixin
from smarter.apps.account.models import Secret
from smarter.apps.plugin.manifest.enum import (
    SAMApiConnectionSpecConnectionKeys,
    SAMApiConnectionSpecKeys,
    SAMApiConnectionStatusKeys,
)
from smarter.apps.plugin.manifest.models.api_connection.enum import AuthMethods
from smarter.apps.plugin.models import ApiConnection
from smarter.apps.plugin.serializers import ApiConnectionSerializer
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

from ..models.api_connection.const import MANIFEST_KIND
from ..models.api_connection.model import SAMApiConnection
from . import SAMConnectionBrokerError


logger = getLogger(__name__)


class SAMApiConnectionBroker(AbstractBroker, AccountMixin):
    """
    Smarter API ApiConnection Manifest Broker.This class is responsible for
    - loading, validating and parsing the Smarter Api yaml ApiConnection manifests
    - using the manifest to initialize the corresponding Pydantic model

    The ApiConnection object provides the generic services for the ApiConnection, such as
    instantiation, create, update, delete, etc.
    """

    # override the base abstract manifest model with the ApiConnection model
    _manifest: SAMApiConnection = None
    _pydantic_model: Type[SAMApiConnection] = SAMApiConnection
    _api_connection: ApiConnection = None
    _api_key_secret: Secret = None
    _proxy_password_secret: Secret = None

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
        user = request.user if hasattr(request, "user") else None
        AccountMixin.__init__(self, account=account, user=user, request=request)

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def model_class(self) -> ApiConnection:
        return ApiConnection

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMApiConnection:
        """
        SAMApiConnection() is a Pydantic model
        that is used to represent the Smarter API ApiConnection manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMApiConnection(
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
        config_dump[SAMMetadataKeys.NAME.value] = self.manifest.metadata.name
        config_dump[SAMMetadataKeys.DESCRIPTION.value] = self.manifest.metadata.description

        # retrieve the apiKey Secret
        config_dump[SAMApiConnectionSpecConnectionKeys.API_KEY.value] = self.get_or_create_secret(
            user_profile=self.user_profile, name=config_dump[SAMApiConnectionSpecConnectionKeys.API_KEY.value]
        )

        # retrieve the proxyUsername Secret, if it exists
        if config_dump.get(SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value):
            config_dump[SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value] = self.get_or_create_secret(
                user_profile=self.user_profile,
                name=config_dump[SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value],
            )
        return config_dump

    @property
    def api_key_secret(self) -> Secret:
        """
        Return the api_key secret for the ApiConnection.
        """
        if self._api_key_secret:
            return self._api_key_secret
        try:
            name = (
                self.manifest.spec.connection.apiKey
                if self.manifest
                else self.api_connection.api_key.name if self.api_connection else None
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
    def proxy_password_secret(self) -> Secret:
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
                    self.api_connection.proxy_password.name
                    if self.api_connection and self.api_connection.proxy_password
                    else None
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
    def api_connection(self) -> ApiConnection:
        if self._api_connection:
            return self._api_connection

        try:
            self._api_connection = ApiConnection.objects.get(account=self.account, name=self.name)
        except ApiConnection.DoesNotExist:
            if self.manifest:
                model_dump = self.manifest.spec.connection.model_dump()
                model_dump = self.camel_to_snake(model_dump)

                model_dump[SAMMetadataKeys.ACCOUNT.value] = self.account
                model_dump[SAMMetadataKeys.NAME.value] = self.manifest.metadata.name
                model_dump[SAMMetadataKeys.VERSION.value] = self.manifest.metadata.version
                model_dump[SAMMetadataKeys.DESCRIPTION.value] = self.manifest.metadata.description
                model_dump[SAMApiConnectionSpecConnectionKeys.API_KEY.value] = self.api_key_secret

                self._api_connection = ApiConnection(**model_dump)
                self._api_connection.save()
                self._created = True

        return self._api_connection

    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        """
        Return an example ApiConnection manifest.
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
    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name: str = kwargs.get(SAMMetadataKeys.NAME.value, None)
        data = []

        # generate a QuerySet of ApiConnection objects that match our search criteria
        if name:
            api_connections = ApiConnection.objects.filter(account=self.account, name=name)
        else:
            api_connections = ApiConnection.objects.filter(account=self.account)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each ApiConnection
        for api_connection in api_connections:
            try:
                model_dump = ApiConnectionSerializer(api_connection).data
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
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=ApiConnectionSerializer()),
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
                if key == SAMApiConnectionSpecConnectionKeys.API_KEY.value:
                    setattr(self.api_connection, key, self.api_key_secret)
                elif key == SAMApiConnectionSpecConnectionKeys.PROXY_PASSWORD.value:
                    setattr(self.api_connection, key, self.proxy_password_secret)
                else:
                    setattr(self.api_connection, key, value)
            self.api_connection.save()
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
            is_valid = self.api_connection.validate()
        except Exception:
            pass

        if self.api_connection:
            try:
                data = model_to_dict(self.api_connection)
                data = self.snake_to_camel(data)
                data.pop("id")
                data.pop(SAMMetadataKeys.NAME.value)
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
                        SAMMetadataKeys.NAME.value: self.api_connection.name,
                        SAMMetadataKeys.DESCRIPTION.value: self.api_connection.description,
                        SAMMetadataKeys.VERSION.value: self.api_connection.version,
                    },
                    SAMKeys.SPEC.value: {SAMApiConnectionSpecKeys.CONNECTION.value: data},
                    SAMKeys.STATUS.value: {
                        SAMApiConnectionStatusKeys.CONNECTION_STRING.value: self.api_connection.get_connection_string(),
                        SAMApiConnectionStatusKeys.IS_VALID.value: is_valid,
                    },
                }
                # validate our results by round-tripping the data through the Pydantic model
                pydantic_model = self.pydantic_model(**retval)
                data = pydantic_model.model_dump_json()
                return self.json_response_ok(command=command, data=retval)
            except Exception as e:
                raise SAMConnectionBrokerError(message=str(e), thing=self.kind, command=command) from e
        raise SAMBrokerErrorNotReady(message="No connection found", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.api_connection:
            try:
                self.api_connection.delete()
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
