# pylint: disable=W0718
"""Smarter API SmarterAuthToken Manifest handler"""

import typing

from django.forms.models import model_to_dict
from django.http import HttpRequest
from rest_framework.serializers import ModelSerializer

from smarter.apps.account.mixins import AccountMixin
from smarter.common.api import SmarterApiVersions
from smarter.lib.drf.manifest.enum import SAMSmarterAuthTokenSpecKeys
from smarter.lib.drf.manifest.models.auth_token.const import MANIFEST_KIND
from smarter.lib.drf.manifest.models.auth_token.model import SAMSmarterAuthToken
from smarter.lib.drf.models import SmarterAuthToken
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)
from smarter.lib.manifest.exceptions import SAMExceptionBase
from smarter.lib.manifest.loader import SAMLoader


if typing.TYPE_CHECKING:
    from smarter.apps.account.models import Account

MAX_RESULTS = 1000


class SAMSmarterAuthTokenBrokerError(SAMExceptionBase):
    """Base exception for Smarter API SmarterAuthToken Broker handling."""


class SmarterAuthTokenSerializer(ModelSerializer):
    """API key serializer for smarter api."""

    # pylint: disable=missing-class-docstring
    class Meta:
        model = SmarterAuthToken
        fields = ["key_id", "name", "description", "is_active", "last_used_at", "created_at", "updated_at"]


class SAMSmarterAuthTokenBroker(AbstractBroker, AccountMixin):
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
    _manifest: SAMSmarterAuthToken = None
    _smarter_auth_token: SmarterAuthToken = None
    _token_key: str = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        request: HttpRequest,
        account: "Account",
        api_version: str = SmarterApiVersions.V1.value,
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

    @property
    def smarter_auth_token(self) -> SmarterAuthToken:
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
            self._smarter_auth_token = SmarterAuthToken.objects.get(
                user=self.user, description=self.manifest.metadata.description
            )
        except SmarterAuthToken.DoesNotExist:
            self._smarter_auth_token, self._token_key = SmarterAuthToken.objects.create(
                name=self.manifest.metadata.name, user=self.user, description=self.manifest.metadata.description
            )

        return self._smarter_auth_token

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API SAMSmarterAuthToken manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        return config_dump

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API SAMSmarterAuthToken manifest dict.
        """
        smarter_auth_token_dict = model_to_dict(self.smarter_auth_token)
        smarter_auth_token_dict = self.snake_to_camel(smarter_auth_token_dict)
        smarter_auth_token_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.smarter_auth_token.name,
                SAMMetadataKeys.DESCRIPTION.value: self.smarter_auth_token.description,
                SAMMetadataKeys.VERSION.value: self.smarter_auth_token.version,
            },
            SAMKeys.SPEC.value: {
                SAMSmarterAuthTokenSpecKeys.CONFIG.value: {
                    "isActive": self.smarter_auth_token.is_active,
                    "username": self.smarter_auth_token.user.username,
                },
            },
            SAMKeys.STATUS.value: {
                "created": self.smarter_auth_token.created_at.isoformat(),
                "modified": self.smarter_auth_token.updated_at.isoformat(),
                "lastUsedAt": self.smarter_auth_token.last_used_at.isoformat(),
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
    def manifest(self) -> SAMSmarterAuthToken:
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
        if self.loader:
            self._manifest = SAMSmarterAuthToken(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=self.loader.manifest_metadata,
                spec=self.loader.manifest_spec,
                status=self.loader.manifest_status,
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def model_class(self) -> SAMSmarterAuthToken:
        return SAMSmarterAuthToken

    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "camelCaseName",
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

    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        data = []
        smarter_auth_tokens = SmarterAuthToken.objects.filter(user=self.user)

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for smarter_auth_token in smarter_auth_tokens:
            try:
                model_dump = SmarterAuthTokenSerializer(smarter_auth_token).data
                if not model_dump:
                    raise SAMSmarterAuthTokenBrokerError(f"Model dump failed for {self.kind} {smarter_auth_token.name}")
                data.append(model_dump)
            except Exception as e:
                return self.json_response_err(command=command, e=e)
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
        readonly_fields = ["id", "created_at", "updated_at", "last_used_at", "key_id", "user", "digest", "token_key"]
        try:
            data = self.manifest_to_django_orm()
            for field in readonly_fields:
                data.pop(field, None)
            for key, value in data.items():
                setattr(self.smarter_auth_token, key, value)
            self.smarter_auth_token.save()
        except Exception as e:
            return self.json_response_err(command=command, e=e)
        return self.json_response_ok(command=command, data={})

    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        if self.smarter_auth_token:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                return self.json_response_err(command=command, e=e)
        return self.json_response_err_notready(command=command)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        if self.smarter_auth_token:
            try:
                self.smarter_auth_token.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                return self.json_response_err(command=command, e=e)
        return self.json_response_err_notready(command=command)

    def deploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        return self.json_response_err_notimplemented(command=command)

    def undeploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        return self.json_response_err_notimplemented(command=command)

    def logs(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        if self.smarter_auth_token:
            data = {}
            return self.json_response_ok(command=command, data=data)
        return self.json_response_err_notready(command=command)
