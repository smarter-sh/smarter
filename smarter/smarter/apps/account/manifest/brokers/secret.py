# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import logging
import traceback
from datetime import datetime, timezone
from typing import Optional, Type

from dateutil.relativedelta import relativedelta
from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework import serializers

from smarter.apps.account.manifest.enum import (
    SAMSecretMetadataKeys,
    SAMSecretSpecKeys,
    SAMSecretStatusKeys,
)
from smarter.apps.account.manifest.models.secret.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.secret.model import (
    SAMSecret,
    SAMSecretMetadata,
    SAMSecretSpec,
)
from smarter.apps.account.manifest.transformers.secret import SecretTransformer
from smarter.apps.account.models import Secret
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.logging import WaffleSwitchedLoggerWrapper
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


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return (
        waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)
        and waffle.switch_is_active(SmarterWaffleSwitches.MANIFEST_LOGGING)
    ) and level >= logging.INFO


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

MAX_RESULTS = 1000


class SecretSerializer(serializers.ModelSerializer):
    """Secret serializer for Smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = Secret
        fields = "__all__"
        read_only_fields = ("user_profile", "last_accessed", "created_at", "modified_at")


class SAMSecretBrokerError(SAMBrokerError):
    """Base exception for Smarter API Secret Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API Secret Manifest Broker Error"


class SAMSecretBroker(AbstractBroker):
    """
    Smarter API Secret Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml Secret manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API Secret manifests. The Broker class is responsible
    for creating, updating, deleting and querying the Django ORM models, as well
    as transforming the Django ORM models into Pydantic models for serialization
    and deserialization.
    """

    # override the base abstract manifest model with the Secret model
    _manifest: Optional[SAMSecret] = None
    _pydantic_model: Type[SAMSecret] = SAMSecret
    _secret_transformer: Optional[SecretTransformer] = None

    @property
    def secret_transformer(self) -> SecretTransformer:
        """
        Return the SecretTransformer instance for this manifest.
        """
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady(
                "User profile is not set. Cannot create SecretTransformer.",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        if not self._secret_transformer:
            self._secret_transformer = SecretTransformer(
                name=self.name, api_version=self.api_version, user_profile=self.user_profile, manifest=self.manifest
            )
        return self._secret_transformer

    @property
    def secret(self) -> Optional[Secret]:
        """
        Return the Secret model instance for this manifest.
        """
        return self.secret_transformer.secret

    def manifest_to_django_orm(self) -> Optional[dict]:
        """
        Transform the Smarter API Secret manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()  # type: ignore[return-value]
        config_dump = self.camel_to_snake(config_dump)
        return config_dump  # type: ignore[return-value]

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API Secret manifest dict.
        """
        if not self.secret:
            logger.warning("%s.django_orm_to_manifest_dict() called with no secret", self.formatted_class_name)
            return None
        secret_dict: dict

        try:
            secret_dict = model_to_dict(self.secret)
            secret_dict = self.snake_to_camel(secret_dict)  # type: ignore[assignment]
            secret_dict.pop("id")
        except Exception as e:
            raise SAMSecretBrokerError(
                f"Failed to serialize {self.kind} {self.secret} into camelCased Python dict",
                thing=self.kind,
                stack_trace=traceback.format_exc(),
            ) from e

        try:
            data = {
                SAMKeys.APIVERSION.value: self.api_version,
                SAMKeys.KIND.value: self.kind,
                SAMKeys.METADATA.value: {
                    SAMSecretMetadataKeys.NAME.value: secret_dict.get(SAMSecretMetadataKeys.NAME.value),
                    SAMSecretMetadataKeys.DESCRIPTION.value: secret_dict.get(SAMSecretMetadataKeys.DESCRIPTION.value),
                    SAMSecretMetadataKeys.VERSION.value: "1.0.0",
                    SAMSecretMetadataKeys.USERNAME.value: self.user.username if self.user else None,
                    SAMSecretMetadataKeys.ACCOUNT_NUMBER.value: self.account.account_number if self.account else None,
                    SAMSecretMetadataKeys.TAGS.value: secret_dict.get(SAMSecretMetadataKeys.TAGS.value),
                    SAMSecretMetadataKeys.ANNOTATIONS.value: secret_dict.get(SAMSecretMetadataKeys.ANNOTATIONS.value),
                },
                SAMKeys.SPEC.value: {
                    SAMSecretSpecKeys.CONFIG.value: {
                        SAMSecretSpecKeys.VALUE.value: self.secret.get_secret(),
                        SAMSecretSpecKeys.DESCRIPTION.value: secret_dict.get(SAMSecretSpecKeys.DESCRIPTION.value),
                        SAMSecretSpecKeys.EXPIRATION_DATE.value: (
                            self.secret.expires_at.isoformat() if self.secret.expires_at else None
                        ),
                    }
                },
                SAMKeys.STATUS.value: {
                    SAMSecretStatusKeys.ACCOUNT_NUMBER.value: self.account_number,
                    SAMSecretStatusKeys.USERNAME.value: self.user.username if self.user else None,
                    SAMSecretStatusKeys.CREATED.value: self.secret.created_at.isoformat(),
                    SAMSecretStatusKeys.UPDATED.value: self.secret.updated_at.isoformat(),
                    SAMSecretStatusKeys.LAST_ACCESSED.value: (
                        self.secret.last_accessed.isoformat() if self.secret.last_accessed else None
                    ),
                },
            }
        except Exception as e:
            raise SAMSecretBrokerError(
                f"Failed to transform {self.kind} {self.secret} into manifest dict",
                thing=self.kind,
                stack_trace=traceback.format_exc(),
            ) from e
        return data

    ###########################################################################
    # Smarter abstract property implementations
    ###########################################################################
    @property
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMSecretBroker()"

    @property
    def kind(self) -> str:
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMSecret]:
        """
        SAMSecret() is a Pydantic model
        that is used to represent the Smarter API Secret manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_metadata and self.loader.manifest_kind == self.kind:
            self._manifest = SAMSecret(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMSecretMetadata(**self.loader.manifest_metadata),
                spec=SAMSecretSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def model_class(self):
        return Secret

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        current_date = datetime.now(timezone.utc)
        expiration_date = current_date + relativedelta(months=6)
        expiration_date_string = expiration_date.date().isoformat()
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMSecretMetadataKeys.NAME.value: "example_secret",
                SAMSecretMetadataKeys.DESCRIPTION.value: "an example secret manifest for the Smarter API Secret",
                SAMSecretMetadataKeys.VERSION.value: "1.0.0",
                SAMSecretMetadataKeys.ACCOUNT_NUMBER.value: SMARTER_ACCOUNT_NUMBER,
                SAMSecretMetadataKeys.USERNAME.value: "admin",
                SAMSecretMetadataKeys.TAGS.value: ["example", "secret"],
                SAMSecretMetadataKeys.ANNOTATIONS.value: [],
            },
            SAMKeys.SPEC.value: {
                SAMSecretSpecKeys.CONFIG.value: {
                    SAMSecretSpecKeys.VALUE.value: "<** your unencrypted credential value **>",
                    SAMSecretSpecKeys.DESCRIPTION.value: "salesforce.com api key",
                    SAMSecretSpecKeys.EXPIRATION_DATE.value: expiration_date_string,
                },
            },
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name = kwargs.get(SAMMetadataKeys.NAME.value, None)
        data = []

        if name:
            secrets = Secret.objects.filter(user_profile=self.user_profile, name=name)
        else:
            secrets = Secret.objects.filter(user_profile=self.user_profile)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for secret in secrets:
            try:
                model_dump = SecretSerializer(secret).data
                if not model_dump:
                    raise SAMSecretBrokerError(
                        f"Model dump failed for {self.kind} {secret}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMSecretBrokerError(
                    f"Model dump failed for {self.kind} {secret}",
                    thing=self.kind,
                    command=command,
                    stack_trace=traceback.format_exc(),
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: self.params,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=SecretSerializer()),
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

        try:
            self.secret_transformer.create()
        except Exception as e:
            return self.json_response_err(command=command, e=e)

        if self.secret_transformer.ready:
            try:
                self.secret_transformer.save()
            except Exception as e:
                return self.json_response_err(command=command, e=e)
            return self.json_response_ok(command=command, data=self.to_json())
        try:
            raise SAMBrokerErrorNotReady(f"Secret {self.name} not ready", thing=self.kind, command=command)
        except SAMBrokerErrorNotReady as err:
            return self.json_response_err(command=command, e=err)

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)
        if self.user_profile is None:
            raise SAMBrokerErrorNotReady(
                "User profile is not set. Cannot describe.",
                thing=self.kind,
                command=command,
            )
        param_name = request.GET.get("name", None)
        kwarg_name = kwargs.get(SAMSecretMetadataKeys.NAME.value, None)
        secret_name = param_name or kwarg_name or self.name
        self._name = secret_name

        self._secret_transformer = SecretTransformer(name=secret_name, user_profile=self.user_profile)
        if not self.secret_transformer.secret:
            raise SAMBrokerErrorNotFound(
                f"Failed to describe {self.kind} {secret_name} belonging to {self.user_profile}. Not found",
                thing=self.kind,
                command=command,
            )

        if self.secret:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMSecretBrokerError(
                    f"Failed to describe {self.kind} {self.secret}",
                    thing=self.kind,
                    command=command,
                    stack_trace=traceback.format_exc(),
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.secret:
            try:
                self.secret.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMSecretBrokerError(
                    f"Failed to delete {self.kind} {self.secret}",
                    thing=self.kind,
                    command=command,
                    stack_trace=traceback.format_exc(),
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(f"{command} not implemented", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(f"{command} not implemented", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(f"{command} not implemented", thing=self.kind, command=command)
