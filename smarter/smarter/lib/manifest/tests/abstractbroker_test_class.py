# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import typing

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.manifest.enum import SAMUserSpecKeys
from smarter.apps.plugin.manifest.models.static_plugin.const import MANIFEST_KIND
from smarter.apps.plugin.manifest.models.static_plugin.model import SAMStaticPlugin
from smarter.lib.django.user import UserType
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import AbstractBroker, SAMBrokerError
from smarter.lib.manifest.enum import SAMKeys, SAMMetadataKeys


MAX_RESULTS = 1000


class SAMUserBrokerError(SAMBrokerError):
    """Base exception for Smarter API User Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API User Manifest Broker Error"


class SAMTestBroker(AbstractBroker):
    """Test class for unit tests of the abstract broker class."""

    # override the base abstract manifest model with the User model
    # FIX NOTE: We shouldn't be using an implementation of the actual
    #           manifest model here. We should be using a test model.
    _manifest: SAMStaticPlugin = None
    _pydantic_model: typing.Type[SAMStaticPlugin] = SAMStaticPlugin
    _user: UserType = None
    _username: str = None

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
    def formatted_class_name(self) -> str:
        """
        Returns the formatted class name for logging purposes.
        This is used to provide a more readable class name in logs.
        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMTestBroker()"

    @property
    def kind(self) -> str:
        # FIX NOTE: WE SHOULD NOT BE USING AN ACTUAL KIND HERE. WE NEED A
        #           TEST KIND FOR THE TESTS.
        return MANIFEST_KIND

    @property
    def manifest(self) -> SAMStaticPlugin:  # FIX NOTE: This should be a test model
        """
        SAMStaticPlugin() is a Pydantic model
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
            self._manifest = SAMStaticPlugin(
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
