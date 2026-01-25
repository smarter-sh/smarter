# pylint: disable=W0718
"""Smarter API SmarterAuthToken Manifest handler"""

import traceback
from logging import getLogger
from typing import Any, Optional, Type

from django.core import serializers
from django.core.handlers.wsgi import WSGIRequest
from pydantic_core import ValidationError as PydanticValidationError
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.models import User
from smarter.apps.account.utils import cache_invalidate
from smarter.lib import json
from smarter.lib.drf.manifest.enum import SAMSmarterAuthTokenSpecKeys
from smarter.lib.drf.manifest.models.auth_token.const import MANIFEST_KIND
from smarter.lib.drf.manifest.models.auth_token.metadata import (
    SAMSmarterAuthTokenMetadata,
)
from smarter.lib.drf.manifest.models.auth_token.model import SAMSmarterAuthToken
from smarter.lib.drf.manifest.models.auth_token.spec import (
    SAMSmarterAuthTokenSpec,
    SAMSmarterAuthTokenSpecConfig,
)
from smarter.lib.drf.manifest.models.auth_token.status import SAMSmarterAuthTokenStatus
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
    _orm_instance: Optional[SmarterAuthToken]

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

        if not self._manifest:
            logger.debug(
                "%s.smarter_auth_token() Manifest not set. Cannot retrieve SmarterAuthToken.",
                self.formatted_class_name,
            )
            return None

        try:
            logger.debug(
                "%s.smarter_auth_token() Retrieving SmarterAuthToken for user %s with name %s",
                self.formatted_class_name,
                self.user,
                self.name,
            )
            self._smarter_auth_token = SmarterAuthToken.objects.get(
                user__username=self.manifest.spec.config.username, name=self.name
            )
        except SmarterAuthToken.DoesNotExist:
            logger.debug(
                "%s.smarter_auth_token() SmarterAuthToken for user %s with name %s does not exist.",
                self.formatted_class_name,
                self.manifest.spec.config.username,
                self.name,
            )
        return self._smarter_auth_token

    @smarter_auth_token.setter
    def smarter_auth_token(self, value: SmarterAuthToken) -> None:
        """
        Set the SmarterAuthToken object.
        """
        self._smarter_auth_token = value
        logger.debug(
            "%s.smarter_auth_token() set to %s",
            self.formatted_class_name,
            self._smarter_auth_token,
        )

    @property
    def token_key(self) -> Optional[str]:
        """
        The token_key is the actual API key that is used to authenticate with the Smarter API.
        The token_key is generated by the SmarterAuthToken object when it is created and
        it is only available immediately after the object is created.
        """
        if self.created and self._token_key:
            return self._token_key

    def manifest_to_django_orm(self) -> dict[str, Any]:
        """
        Transform the Smarter API SAMSmarterAuthToken manifest into a Django ORM model.
        """
        logger.debug("%s.manifest_to_django_orm() called", self.formatted_class_name)
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        if not isinstance(config_dump, dict):
            raise SAMSmarterAuthTokenBrokerError(
                message=f"Invalid config dump for {self.kind} manifest: {config_dump}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        if self.smarter_auth_token is None:
            raise SAMBrokerErrorNotReady(
                f"SmarterAuthToken not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )
        if self.manifest is None:
            raise SAMBrokerErrorNotReady(
                f"Manifest not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=SmarterJournalCliCommands.APPLY,
            )

        return {
            "account": self.account,
            "name": self.manifest.metadata.name,
            "description": self.manifest.metadata.description,
            "version": self.manifest.metadata.version,
            "annotations": json.loads(json.dumps(self.manifest.metadata.annotations)),
            **config_dump,
        }

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API SAMSmarterAuthToken manifest dict.
        """
        logger.debug("%s.django_orm_to_manifest_dict() called", self.formatted_class_name)
        if not isinstance(self.smarter_auth_token, SmarterAuthToken):
            raise SAMSmarterAuthTokenBrokerError(
                f"smarter_auth_token is not a SmarterAuthToken instance: {type(self.smarter_auth_token)}",
                thing=self.kind,
                command=None,
            )
        if self.manifest is None:
            raise SAMBrokerErrorNotFound(
                f"Manifest not set for {self.kind} broker. Cannot describe.",
                thing=self.thing,
                command=SmarterJournalCliCommands.DESCRIBE,
            )

        data = self.manifest.model_dump()
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
            if not isinstance(self._manifest, SAMSmarterAuthToken):
                raise SAMSmarterAuthTokenBrokerError(
                    f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                )
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            try:
                logger.debug(
                    "%s.manifest() initializing SAMSmarterAuthToken() using data from self.loader %s",
                    self.formatted_class_name,
                    self.loader,
                )
                self._manifest = SAMSmarterAuthToken(
                    apiVersion=self.loader.manifest_api_version,
                    kind=self.loader.manifest_kind,
                    metadata=SAMSmarterAuthTokenMetadata(**self.loader.manifest_metadata),
                    spec=SAMSmarterAuthTokenSpec(**self.loader.manifest_spec),
                )
                logger.debug(
                    "%s.manifest() initialized with SAMSmarterAuthToken() using data from self.loader",
                    self.formatted_class_name,
                )
            except PydanticValidationError as e:
                logger.error(
                    "%s.manifest() could not be initialized with SAMSmarterAuthToken() using data from self.loader: %s",
                    self.formatted_class_name,
                    str(e),
                )
        elif self.smarter_auth_token:
            status = SAMSmarterAuthTokenStatus(
                created=self.smarter_auth_token.created_at,
                modified=self.smarter_auth_token.updated_at,
                lastUsedAt=self.smarter_auth_token.last_used_at,
            )
            metadata = SAMSmarterAuthTokenMetadata(
                name=str(self.smarter_auth_token.name),
                description=self.smarter_auth_token.description,
                version=self.smarter_auth_token.version,
                tags=self.smarter_auth_token.tags,
                annotations=self.smarter_auth_token.annotations,
            )
            spec = SAMSmarterAuthTokenSpec(
                config=SAMSmarterAuthTokenSpecConfig(
                    isActive=self.smarter_auth_token.is_active,
                    username=self.smarter_auth_token.user.username,
                )
            )
            self._manifest = SAMSmarterAuthToken(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=metadata,
                spec=spec,
                status=status,
            )
            logger.debug(
                "%s.manifest() initialized %s from SmarterAuthToken ORM model %s: %s",
                self.formatted_class_name,
                type(self._manifest).__name__,
                self.smarter_auth_token,
                serializers.serialize("json", [self.smarter_auth_token]),
            )
            return self._manifest
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
    def SerializerClass(self) -> Type[ModelSerializer]:
        """
        Return the Serializer class for the SmarterAuthToken model.
        This is used to serialize and deserialize the SmarterAuthToken
        model for API responses and requests.
        """
        return SmarterAuthTokenSerializer

    @property
    def ORMModelClass(self) -> Type[SmarterAuthToken]:
        return SmarterAuthToken

    @property
    def orm_instance(self) -> Optional[SmarterAuthToken]:
        """
        Return the Django ORM model instance for the broker.

        :return: The Django ORM model instance for the broker.
        :rtype: Optional[TimestampedModel]
        """
        if self._orm_instance:
            return self._orm_instance

        if not self._manifest:
            logger.debug(
                "%s.orm_instance() - manifest is not set. Cannot retrieve ORM instance.",
                self.abstract_broker_logger_prefix,
            )
            return None
        try:
            logger.debug(
                "%s.orm_instance() - attempting to retrieve ORM instance %s for user=%s, name=%s",
                self.abstract_broker_logger_prefix,
                SmarterAuthToken.__name__,
                self.user,
                self.name,
            )
            instance = SmarterAuthToken.objects.get(user__username=self.manifest.spec.config.username, name=self.name)
            logger.debug(
                "%s.orm_instance() - retrieved ORM instance: %s",
                self.abstract_broker_logger_prefix,
                serializers.serialize("json", [instance]),
            )
            return instance
        except SmarterAuthToken.DoesNotExist:
            logger.warning(
                "%s.orm_instance() - ORM instance does not exist for account=%s, name=%s",
                self.abstract_broker_logger_prefix,
                self.account,
                self.name,
            )
            return None

    def example_manifest(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        logger.debug("%s.example_manifest() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
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
        logger.debug("%s.get() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
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
        logger.debug("%s.apply() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        super().apply(request, kwargs)
        command = self.apply.__name__
        command = SmarterJournalCliCommands(command)
        readonly_fields = [
            "id",
            "created_at",
            "updated_at",
            "last_used_at",
            "key_id",
            "user",
            "username",
            "digest",
            "token_key",
        ]

        if not self.user.is_staff:
            raise SAMSmarterAuthTokenBrokerError(
                message="Only account admins can apply auth token manifests.",
                thing=self.kind,
                command=command,
            )

        if not self.manifest:
            raise SAMBrokerErrorNotReady(
                f"Manifest not set for {self.kind} broker. Cannot apply.",
                thing=self.thing,
                command=command,
            )
        if self.smarter_auth_token is None:
            self.smarter_auth_token = SmarterAuthToken(
                user=self.user,
                account=self.account,
            )
        try:
            data = self.manifest_to_django_orm()
            for field in readonly_fields:
                logger.debug(
                    "%s.apply() Removing readonly field %s from data for %s",
                    self.formatted_class_name,
                    field,
                    self.kind,
                )
                data.pop(field, None)
            for key, value in data.items():
                setattr(self.smarter_auth_token, key, value)
                logger.debug("%s.apply() Setting %s to %s", self.formatted_class_name, key, value)

            # handle the username
            try:
                manifest_spec_config_user = User.objects.get(username=self.manifest.spec.config.username)
            except User.DoesNotExist as e:
                raise SAMSmarterAuthTokenBrokerError(
                    f"User {self.manifest.spec.config.username} does not exist for {self.kind} {self.name}",
                    thing=self.kind,
                    command=command,
                ) from e

            # ensure that the role of the user is equal to or less than the role of the owner
            # of this process.
            if not self.user.is_staff and not self.user.is_superuser:
                raise SAMSmarterAuthTokenBrokerError(
                    f"User {self.user.username} does not have permission to create or modify API keys.",
                    thing=self.kind,
                    command=command,
                )
            if not self.user.is_superuser:
                if manifest_spec_config_user.is_superuser:
                    raise SAMSmarterAuthTokenBrokerError(
                        f"User {self.user.username} does not have permission to create or modify API keys for users with higher administrative roles.",
                        thing=self.kind,
                        command=command,
                    )

            self.smarter_auth_token.user = manifest_spec_config_user
            logger.debug(
                "%s.apply() Setting smarter_auth_token.user to %s",
                self.formatted_class_name,
                manifest_spec_config_user,
            )

            logger.debug(
                "%s.apply() Saving %s: %s",
                self.formatted_class_name,
                self.smarter_auth_token,
                serializers.serialize("json", [self.smarter_auth_token]),
            )
            self.smarter_auth_token.save()
            tags = set(self.manifest.metadata.tags) if self.manifest.metadata.tags else set()
            logger.debug(
                "%s.apply() Setting tags for %s to %s",
                self.formatted_class_name,
                self.smarter_auth_token,
                tags,
            )
            self.smarter_auth_token.tags = list(tags)
            self.smarter_auth_token.save()
            self.smarter_auth_token.refresh_from_db()
            cache_invalidate(user=self.user, account=self.smarter_auth_token)  # type: ignore
            logger.debug(
                "%s.apply() Saved %s: %s",
                self.formatted_class_name,
                self.smarter_auth_token,
                serializers.serialize("json", [self.smarter_auth_token]),
            )
        except Exception as e:
            tb = traceback.format_exc()
            raise SAMBrokerError(message=f"Error in {command}: {e}\n{tb}", thing=self.kind, command=command) from e
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        logger.debug("%s.chat() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        logger.debug(
            "%s.describe() called for %s with args: %s, kwargs: %s", self.formatted_class_name, self.name, args, kwargs
        )
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
        logger.debug(
            "%s.delete() called for %s with args: %s, kwargs: %s", self.formatted_class_name, self.name, args, kwargs
        )
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)

        if not self.user.is_staff:
            raise SAMSmarterAuthTokenBrokerError(
                message="Only account admins can delete auth tokens.",
                thing=self.kind,
                command=command,
            )

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
        logger.debug(
            "%s.deploy() called for %s with args: %s, kwargs: %s", self.formatted_class_name, self.name, args, kwargs
        )
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)

        if not self.smarter_auth_token:
            self.apply(request, *args, **kwargs)

        if self.smarter_auth_token:
            if not self.smarter_auth_token.is_active:
                self.smarter_auth_token.is_active = True
                self.smarter_auth_token.save()
        else:
            logger.error(
                "%s.deploy() - %s %s is not ready after apply(). manifest: %s, loader: %s",
                self.formatted_class_name,
                self.kind,
                self.name,
                self.manifest,
                self.loader,
            )
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)
        return self.json_response_ok(command=command, data=self.to_json())

    def undeploy(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        logger.debug(
            "%s.undeploy() called for %s with args: %s, kwargs: %s", self.formatted_class_name, self.name, args, kwargs
        )
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        self.set_and_verify_name_param(command=command)

        if self.smarter_auth_token:
            if self.smarter_auth_token.is_active:
                self.smarter_auth_token.is_active = False
                self.smarter_auth_token.save()
                self.smarter_auth_token.refresh_from_db()
        else:
            raise SAMBrokerErrorNotReady(f"{self.kind} {self.name} is not ready", thing=self.kind, command=command)
        return self.json_response_ok(command=command, data=self.to_json())

    def logs(self, request: WSGIRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        logger.debug("%s.logs() called with args: %s, kwargs: %s", self.formatted_class_name, args, kwargs)
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Logs are not implemented", thing=self.kind, command=command)
