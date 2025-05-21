# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import typing

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.manifest.enum import SAMUserSpecKeys
from smarter.apps.account.manifest.models.user.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.user.model import SAMUser
from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account, AccountContact, UserProfile
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.serializers import UserSerializer
from smarter.lib.django.user import get_user_model
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
from smarter.lib.manifest.loader import SAMLoader


User = get_user_model()
MAX_RESULTS = 1000


class SAMUserBrokerError(SAMBrokerError):
    """Base exception for Smarter API User Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API User Manifest Broker Error"


class SAMUserBroker(AbstractBroker, AccountMixin):
    """
    Smarter API User Manifest Broker. This class is responsible for
    - loading, validating and parsing the Smarter Api yaml User manifests
    - using the manifest to initialize the corresponding Pydantic model

    This Broker class interacts with the collection of Django ORM models that
    represent the Smarter API User manifests. The Broker class is responsible
    for creating, updating, deleting and querying the Django ORM models, as well
    as transforming the Django ORM models into Pydantic models for serialization
    and deserialization.
    """

    # override the base abstract manifest model with the User model
    _manifest: SAMUser = None
    _pydantic_model: typing.Type[SAMUser] = SAMUser
    _account_contact: AccountContact = None

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
        AccountMixin.__init__(self, account=account, user=request.user)
        username: str = self.params.get("username", self.user.username if self.user else None)
        if username:
            try:
                self.user = User.objects.get(username=username)
            except User.DoesNotExist as e:
                raise SAMBrokerErrorNotFound(
                    f"Failed to load {self.kind} {username}. Not found", thing=self.kind
                ) from e

    @property
    def account_contact(self) -> AccountContact:
        if self._account_contact:
            return self._account_contact
        if not self.user:
            return None
        if not self.user.is_authenticated:
            return None
        try:
            self._account_contact = AccountContact.objects.get(account=self.account, email=self.user.email)
        except AccountContact.DoesNotExist:
            pass
        return self._account_contact

    @property
    def username(self) -> str:
        return self.user.username if self.user else None

    def manifest_to_django_orm(self) -> dict:
        """
        Transform the Smarter API User manifest into a Django ORM model.
        """
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        return config_dump

    def django_orm_to_manifest_dict(self) -> dict:
        """
        Transform the Django ORM model into a Pydantic readable
        Smarter API User manifest dict.
        """
        user_dict = model_to_dict(self.user)
        user_dict = self.snake_to_camel(user_dict)
        user_dict.pop("id")

        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: self.user.username,
                SAMMetadataKeys.DESCRIPTION.value: self.user.username,
                SAMMetadataKeys.VERSION.value: "1.0.0",
                "username": self.user.username,
            },
            SAMKeys.SPEC.value: {
                SAMUserSpecKeys.CONFIG.value: user_dict,
            },
            SAMKeys.STATUS.value: {
                "dateJoined": self.user.date_joined.isoformat(),
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
    def manifest(self) -> SAMUser:
        """
        SAMUser() is a Pydantic model
        that is used to represent the Smarter API User manifest. The Pydantic
        model is initialized with the data from the manifest loader, which is
        generally passed to the model constructor as **data. However, this top-level
        manifest model has to be explicitly initialized, whereas its child models
        are automatically cascade-initialized by the Pydantic model, implicitly
        passing **data to each child's constructor.
        """
        if self._manifest:
            return self._manifest
        if self.loader:
            self._manifest = SAMUser(
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
    def model_class(self):
        return User

    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "example_user",
                SAMMetadataKeys.DESCRIPTION.value: "an example user manifest for the Smarter API User",
                SAMMetadataKeys.VERSION.value: "1.0.0",
                "username": "example_user",
            },
            SAMKeys.SPEC.value: {
                SAMUserSpecKeys.CONFIG.value: {
                    "firstName": self.account_contact.first_name if self.account_contact else "John",
                    "lastName": self.account_contact.last_name if self.account_contact else "Doe",
                    "email": self.user.email if self.user and self.user.is_authenticated else "joe@mail.com",
                    "isStaff": self.user.is_staff if self.user and self.user.is_authenticated else False,
                    "isActive": self.user.is_active if self.user and self.user.is_authenticated else True,
                },
            },
        }
        return self.json_response_ok(command=command, data=data)

    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        data = []
        user_profiles = UserProfile.objects.filter(account=self.account)
        users = [user_profile.user for user_profile in user_profiles]

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for user in users:
            try:
                model_dump = UserSerializer(user).data
                if not model_dump:
                    raise SAMUserBrokerError(
                        f"Model dump failed for {self.kind} {user.username}", thing=self.kind, command=command
                    )
                camel_cased_model_dump = self.snake_to_camel(model_dump)
                data.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Model dump failed for {self.kind} {user.username}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            SCLIResponseGet.KWARGS.value: self.params,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: self.get_model_titles(serializer=UserSerializer()),
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
        readonly_fields = ["id", "date_joined", "last_login", "username", "is_superuser"]
        try:
            data = self.manifest_to_django_orm()
            for field in readonly_fields:
                data.pop(field, None)
            for key, value in data.items():
                setattr(self.user, key, value)
            self.user.save()
        except Exception as e:
            raise SAMUserBrokerError(
                f"Failed to apply {self.kind} {self.user.email}", thing=self.kind, command=command
            ) from e
        return self.json_response_ok(command=command, data={})

    def chat(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        try:
            self._user = User.objects.get(username=self.username)
        except User.DoesNotExist as e:
            raise SAMBrokerErrorNotFound(
                f"Failed to describe {self.kind} {self.username}. Not found", thing=self.kind, command=command
            ) from e

        try:
            self._user_profile = UserProfile.objects.get(user=self._user, account=self.account)
        except UserProfile.DoesNotExist as e:
            raise SAMBrokerErrorNotFound(
                f"Failed to describe {self.kind} {self.username}. User is not associated with your account",
                thing=self.kind,
                command=command,
            ) from e

        if self.user:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Failed to describe {self.kind} {self.user.email}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)
        if self.user:
            try:
                self.user.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Failed to delete {self.kind} {self.user.email}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.deploy.__name__
        command = SmarterJournalCliCommands(command)
        if self.user:
            try:
                if not self.user.is_active:
                    self.user.is_active = True
                    self.user.save()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Failed to deploy {self.kind} {self.user.email}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def undeploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.undeploy.__name__
        command = SmarterJournalCliCommands(command)
        if self.user:
            try:
                if self.user.is_active:
                    self.user.is_active = False
                    self.user.save()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Failed to deploy {self.kind} {self.user.email}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def logs(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
