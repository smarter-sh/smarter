# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import typing

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.manifest.enum import SAMUserSpecKeys
from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account, UserProfile
from smarter.apps.plugin.manifest.models.plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.plugin.model import SAMPlugin
from smarter.common.api import SmarterApiVersions
from smarter.lib.django.user import UserType
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
)
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.loader import SAMLoader


MAX_RESULTS = 1000


class SAMUserBrokerError(SAMBrokerError):
    """Base exception for Smarter API User Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API User Manifest Broker Error"


class SAMTestBroker(AbstractBroker, AccountMixin):
    """Test class for unit tests of the abstract broker class."""

    # override the base abstract manifest model with the User model
    _manifest: SAMPlugin = None
    _pydantic_model: typing.Type[SAMPlugin] = SAMPlugin
    _user: UserType = None
    _username: str = None

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
        self._username: str = self.params.get("username", None)
        if self._username:
            try:
                self._user = None
                self._user_profile = UserProfile.objects.get(user=self.user, account=self.account)
            except UserProfile.DoesNotExist as e:
                raise SAMBrokerErrorNotFound(
                    message=f"{self.kind} {self._username} not found in your account.",
                    thing=self.kind,
                    command=SmarterJournalCliCommands.GET,
                ) from e

    @property
    def username(self) -> str:
        return self._username

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
    def manifest(self) -> SAMPlugin:
        """
        SAMPlugin() is a Pydantic model
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
            self._manifest = SAMPlugin(
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

    def chat(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        super().chat(request=request, kwargs=kwargs)

    def describe(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        super().describe(request=request, kwargs=kwargs)

    def delete(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        super().delete(request=request, kwargs=kwargs)

    def deploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        super().deploy(request=request, kwargs=kwargs)

    def example_manifest(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        super().example_manifest(request=request, kwargs=kwargs)

    def get(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        super().get(request=request, kwargs=kwargs)

    def logs(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        super().logs(request=request, kwargs=kwargs)

    def undeploy(self, request: HttpRequest, kwargs: dict) -> SmarterJournaledJsonResponse:
        super().undeploy(request=request, kwargs=kwargs)
