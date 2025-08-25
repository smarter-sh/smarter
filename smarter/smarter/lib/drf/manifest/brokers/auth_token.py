# pylint: disable=W0718
"""Smarter API SmarterAuthToken Manifest handler"""

from logging import getLogger
from typing import Any, Optional, Type

from django.core.handlers.wsgi import WSGIRequest
from django.forms.models import model_to_dict
from pydantic_core import ValidationError as PydanticValidationError
from rest_framework.serializers import ModelSerializer

from smarter.lib.drf.manifest.enum import SAMSmarterAuthTokenSpecKeys
from smarter.lib.drf.manifest.models.auth_token.const import MANIFEST_KIND
from smarter.lib.drf.manifest.models.auth_token.metadata import (
    SAMSmarterAuthTokenMetadata,
)
from smarter.lib.drf.manifest.models.auth_token.model import SAMSmarterAuthToken
from smarter.lib.drf.manifest.models.auth_token.spec import SAMSmarterAuthTokenSpec
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)


MAX_RESULTS = 1000
logger = getLogger(__name__)


class SAMSmarterAuthTokenBrokerError(SAMBrokerError):
    """Base exception for Smarter API SmarterAuthToken Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API SmarterAuthToken Manifest Broker Error"


class SmarterAuthTokenSerializer(ModelSerializer):
    """API key serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SmarterAuthToken
        fields = ["key_id", "name", "description", "is_active", "last_used_at", "created_at", "updated_at"]


class SAMSmarterAuthTokenBroker(AbstractBroker):
    """
    Smarter API SmarterAuthToken Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml SmarterAuthToken manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API SAMSmarterAuthToken manifests. The Broker class
    is responsible for creating, updating, deleting and querying the Django ORM
    models, as well as transforming the Django ORM models into Pydantic models
    for serialization and deserialization.
    """

    # override the base abstract manifest model with the SAMSmarterAuthToken model
    _manifest: Optional[SAMSmarterAuthToken]
    _pydantic_model: Type[SAMSmarterAuthToken] = SAMSmarterAuthToken
    _smarter_auth_token: Optional[SmarterAuthToken]
    _token_key: Optional[str]

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMSmarterAuthTokenBroker with the given arguments.
        The constructor initializes the parent class and sets up the manifest
        and user attributes.
        """
        self._smarter_auth_token = None
        self._token_key = None
        self._created = False
        super().__init__(*args, **kwargs)

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMSmarterAuthTokenBroker()"

    @property
    def smarter_auth_token(self) -> Optional[SmarterAuthToken]:
        """
        The SmarterAuthToken object is a Django ORM model subclass from knox.AuthToken
        that represents a SmarterAuthToken api key. The SmarterAuthToken object is
        used to store the authentication hash and Smarter metadata for the Smarter API.
        The SmarterAuthToken object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._smarter_auth_token:
            return self._smarter_auth_token

        try:
            self._smarter_auth_token = SmarterAuthToken.objects.get(user=self.user, name=self.name)
        except SmarterAuthToken.DoesNotExist as e:
            if self.manifest and self.manifest.metadata and self.user:
                self._smarter_auth_token, self._token_key = SmarterAuthToken.objects.create(  # type: ignore[return-value]
                    name=self.manifest.metadata.name, user=self.user, description=self.manifest.metadata.description
                )
                self._created = True
            else:
                raise SAMBrokerErrorNotFound(
                    f"{self.kind} {self.name} does not exist and it could not be created because manifest is None",
                    thing=self.kind,
                    command=None,
                ) from e

        return self._smarter_auth_token

    def to_json(self) -> Optional[dict[str, Any]]:
        """
        A dictionary representation of the SmarterAuthToken object.
        This is used to serialize the object to JSON for the API response.
        """
        if self._smarter_auth_token:
            return SmarterAuthTokenSerializer(self.smarter_auth_token).data
        return None

    @property
    def token_key(self) -> Optional[str]:
        """
        The token_key is the actual API key that is used to authenticate with the Smarter API.
        The token_key is generated by the SmarterAuthToken object when it is created and
        it is only available immediately after the object is created.
        """
        if self.created and self._token_key:
            return self._token_key

    def manifest_to_django_orm(self) -> Optional[dict[str, Any]]:
        """
        Transform the Smarter API SAMSmarterAuthToken manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump() if self.manifest and self.manifest.spec else None
        if not config_dump:
            raise SAMSmarterAuthTokenBrokerError(
                f"Manifest spec config is None for {self.kind} {self.name}",
                thing=self.kind,
                command=None,
            )
        config_dump = self.camel_to_snake(config_dump)
        if isinstance(config_dump, dict):
            config_dump["description"] = (
                self.manifest.metadata.description if self.manifest and self.manifest.metadata else None
            )
        return config_dump if isinstance(config_dump, dict) else None

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API SAMSmarterAuthToken manifest dict.
        """
        if not isinstance(self.smarter_auth_token, SmarterAuthToken):
            raise SAMSmarterAuthTokenBrokerError(
                f"smarter_auth_token is not a SmarterAuthToken instance: {type(self.smarter_auth_token)}",
                thing=self.kind,
                command=None,
            )
        smarter_auth_token_dict = model_to_dict(self.smarter_auth_token)
        smarter_auth_token_dict = self.snake_to_camel(smarter_auth_token_dict)

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.smarter_auth_token.name,
                SAMMetadataKeys.DESCRIPTION.value: self.smarter_auth_token.description,
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: {
                SAMSmarterAuthTokenSpecKeys.CONFIG.value: {
                    "isActive": self.smarter_auth_token.is_active,
                    "username": self.smarter_auth_token.user.username,
                },
            },
            SAMKeys.STATUS.value: {
                "created": (
                    self.smarter_auth_token.created_at.isoformat() if self.smarter_auth_token.created_at else None
                ),
                "modified": (
                    self.smarter_auth_token.updated_at.isoformat() if self.smarter_auth_token.updated_at else None
                ),
                "lastUsedAt": (
                    self.smarter_auth_token.last_used_at.isoformat() if self.smarter_auth_token.last_used_at else None
                ),
            },
        }
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSmarterAuthToken]:
        """
        SAMSmarterAuthToken() is a Pydantic model
        that is used to represent the Smarter API SAMSmarterAuthToken manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:

            try:
                self._manifest = SAMSmarterAuthToken(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMSmarterAuthTokenMetadata(**self.loader.manifest_metadata),
                    spec=SAMSmarterAuthTokenSpec(**self.loader.manifest_spec),
                )
                logger.info(
                    "%s.manifest() initialized with SAMSmarterAuthToken() using data from self.loader", self.kind
                )
            except PydanticValidationError as e:
                logger.error(
                    "%s.manifest() could not be initialized with SAMSmarterAuthToken() using data from self.loader: %s",
                    self.kind,
                    str(e),
                )
        else:
            logger.warning(
                "%s.manifest() %s could not be initialized. self.loader is %s.",
                self.kind,
                self.formatted_class_name,
                "initialized" if self.loader is not None else "not initialized",
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def model_class(self) -> Type[SAMSmarterAuthToken]:
        return SAMSmarterAuthToken

    def example_manifest(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "snake-case-name",
                SAMMetadataKeys.DESCRIPTION.value: "An example Smarter API manifest for a SmarterAuthToken",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: {
                SAMSmarterAuthTokenSpecKeys.CONFIG.value: {
                    "isActive": True,
                    "username": "valid_smarter_username",
                },
            },
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)

        data = []
        name = kwargs.get(SAMMetadataKeys.NAME.value)
        url = self.smarter_build_absolute_uri(request) or "Unknown URL"
        name = self.clean_cli_param(param=name, param_name="name", url=url)

        if name:
            # if the name is not None, then we are looking for a specific SmarterAuthToken
            smarter_auth_tokens = SmarterAuthToken.objects.filter(user=self.user, name=name)
        else:
            smarter_auth_tokens = SmarterAuthToken.objects.filter(user=self.user)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for smarter_auth_token in smarter_auth_tokens:
            try:
                model_dump = SmarterAuthTokenSerializer(smarter_auth_token).data
                if not model_dump:
                    raise SAMSmarterAuthTokenBrokerError(
                        f"Model dump failed for {self.kind} {smarter_auth_token.name}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"Model dump failed for {self.kind} {smarter_auth_token.name}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: kwargs,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=SmarterAuthTokenSerializer()),
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        readonly_fields = ["id", "created_at", "updated_at", "last_used_at", "key_id", "user", "digest", "token_key"]
        self._smarter_auth_token = None
        self._name = self.params.get("name", "MissingName") if self.params else "MissingName"
        message: Optional[str] = None
        if isinstance(self.smarter_auth_token, SmarterAuthToken):
            try:
                data = self.manifest_to_django_orm()
                if isinstance(data, dict):
                    for field in readonly_fields:
                        data.pop(field, None)
                    for key, value in data.items():
                        setattr(self.smarter_auth_token, key, value)
                    self.smarter_auth_token.save()
            except Exception as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"Failed to apply {self.kind} {self.smarter_auth_token.name}", thing=self.kind, command=command
                ) from e
        if self.created and isinstance(self.smarter_auth_token, SmarterAuthToken):
            message = f"Successfully created {self.kind} {self.smarter_auth_token.name} with secret token {self.token_key}. Please store this token securely. It will not be shown again."
        return self.json_response_ok(command=command, data=self.to_json(), message=message)

    def chat(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        self._smarter_auth_token = None
        self.set_and_verify_name_param(command=command)

        if self.smarter_auth_token:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"{self.kind} {self.smarter_auth_token.name} error: {str(e)}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)

    def delete(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)
        if self.smarter_auth_token:
            try:
                self.smarter_auth_token.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"Failed to delete {self.kind} {self.smarter_auth_token.name}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)

    def deploy(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)

        if self.smarter_auth_token:
            if not self.smarter_auth_token.is_active:
                self.smarter_auth_token.is_active = True
                self.smarter_auth_token.save()
        else:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)
        return self.json_response_ok(command=command, data=self.to_json())

    def undeploy(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)

        if self.smarter_auth_token:
            if self.smarter_auth_token.is_active:
                self.smarter_auth_token.is_active = False
                self.smarter_auth_token.save()
        else:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)
        return self.json_response_ok(command=command, data=self.to_json())

    def logs(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Logs are not implemented", thing=self.kind, command=command)
