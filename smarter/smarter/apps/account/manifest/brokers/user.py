# pylint: disable=W0718
"""Smarter API User Manifest handler"""

from django.forms.models import model_to_dict
from django.http import HttpRequest, JsonResponse

from smarter.apps.account.manifest.enum import SAMUserSpecKeys
from smarter.apps.account.manifest.models.user.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.user.model import SAMUser
from smarter.apps.account.mixins import AccountMixin
from smarter.apps.account.models import Account, UserProfile
from smarter.lib.django.user import User, UserType
from smarter.lib.manifest.broker import AbstractBroker
from smarter.lib.manifest.enum import SAMApiVersions, SAMKeys, SAMMetadataKeys
from smarter.lib.manifest.exceptions import SAMExceptionBase
from smarter.lib.manifest.loader import SAMLoader


MAX_RESULTS = 1000


class SAMUserBrokerError(SAMExceptionBase):
    """Base exception for Smarter API User Broker handling."""


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
    _user: UserType = None

    # pylint: disable=too-many-arguments
    def __init__(
        self,
        account: Account,
        api_version: str = SAMApiVersions.V1.value,
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
    def user(self) -> UserType:
        """
        The User object is a Django ORM model that represents the Smarter User.
        The User object is used to store the configuration and state of the User
        in the database. The User object is retrieved from the database, if it exists,
        or created from the manifest if it does not.
        """
        if self._user:
            return self._user
        try:
            self._user = User.objects.get(account=self.account, username=self.manifest.metadata.username)
        except User.DoesNotExist:
            data = self.manifest_to_django_orm()
            self._user = User.objects.create(**data)

        return self._user

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
                SAMMetadataKeys.DESCRIPTION.value: self.user.get_full_name(),
                SAMMetadataKeys.VERSION.value: "1.0.0",
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

    def example_manifest(self, kwargs: dict = None) -> JsonResponse:
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {
                SAMMetadataKeys.NAME.value: "ExampleUser",
                SAMMetadataKeys.DESCRIPTION.value: "an example user manifest for the Smarter API User",
                SAMMetadataKeys.VERSION.value: "1.0.0",
            },
            SAMKeys.SPEC.value: {
                SAMUserSpecKeys.CONFIG.value: {
                    "firstName": self.user.first_name or "John",
                    "lastName": self.user.last_name or "Doe",
                    "email": self.user.email or "joe@mail.com",
                    "isStaff": self.user.is_staff or False,
                    "isActive": self.user.is_active or True,
                },
            },
        }
        return self.success_response(operation=self.example_manifest.__name__, data=data)

    def get(self, request: HttpRequest, args: list, kwargs: dict) -> JsonResponse:
        data = []
        user_profiles = UserProfile.objects.filter(account=self.account)
        users = [user_profile.user for user_profile in user_profiles]
        if not users.exists():
            return self.not_found_response()

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for user in users:
            try:
                model_dump = user.model_dump_json()
                if not model_dump:
                    raise SAMUserBrokerError(f"Model dump failed for {self.kind} {user.name}")
                data.append(model_dump)
            except Exception as e:
                return self.err_response(self.get.__name__, e)
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(data)},
            "kwargs": kwargs,
            "data": {
                "titles": self.get_model_titles(),
                "items": data,
            },
        }
        return self.success_response(operation=self.get.__name__, data=data)

    def apply(self, request: HttpRequest = None) -> JsonResponse:
        try:
            data = self.manifest_to_django_orm()
            for key, value in data.items():
                setattr(self.user, key, value)
            self.user.save()
        except Exception as e:
            return self.err_response(self.apply.__name__, e)
        return self.success_response(operation=self.apply.__name__, data={})

    def describe(self, request: HttpRequest = None) -> JsonResponse:
        if self.user:
            try:
                data = self.django_orm_to_manifest_dict()
                return self.success_response(operation=self.describe.__name__, data=data)
            except Exception as e:
                return self.err_response(self.describe.__name__, e)
        return self.not_ready_response()

    def delete(self, request: HttpRequest = None) -> JsonResponse:
        if self.user:
            try:
                self.user.delete()
                return self.success_response(operation=self.delete.__name__, data={})
            except Exception as e:
                return self.err_response(self.delete.__name__, e)
        return self.not_ready_response()

    def deploy(self, request: HttpRequest = None) -> JsonResponse:
        if self.user:
            try:
                self.user.deployed = True
                self.user.save()
                return self.success_response(operation=self.deploy.__name__, data={})
            except Exception as e:
                return self.err_response(self.deploy.__name__, e)
        return self.not_ready_response()

    def logs(self, request: HttpRequest = None) -> JsonResponse:
        data = {}
        return self.success_response(operation=self.logs.__name__, data=data)
