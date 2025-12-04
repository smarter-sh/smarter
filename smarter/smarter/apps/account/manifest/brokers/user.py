# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import logging
from typing import Optional, Type

from django.forms.models import model_to_dict
from django.http import HttpRequest

from smarter.apps.account.manifest.enum import SAMUserSpecKeys
from smarter.apps.account.manifest.models.user.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.user.model import (
    SAMUser,
    SAMUserMetadata,
    SAMUserSpec,
)
from smarter.apps.account.models import AccountContact, User, UserProfile
from smarter.apps.account.serializers import UserSerializer
from smarter.apps.account.utils import get_cached_user_profile
from smarter.common.conf import settings as smarter_settings
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
    ) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)

MAX_RESULTS = 1000
"""
Maximum number of results to return for list operations.
This limit helps prevent performance issues and excessive data retrieval.

TODO: Make this configurable via smarter_settings.
"""


class SAMUserBrokerError(SAMBrokerError):
    """Base exception for Smarter API User Broker handling."""

    @property
    def get_formatted_err_message(self):
        return "Smarter API User Manifest Broker Error"


class SAMUserBroker(AbstractBroker):
    """
    Smarter API User Manifest Broker

    This class manages the lifecycle of Smarter API User manifests, including loading, validating, parsing, and mapping them to Django ORM models and Pydantic models for serialization and deserialization.

    **Responsibilities:**
      - Load and validate Smarter API YAML User manifests.
      - Parse manifests and initialize the corresponding Pydantic model (`SAMUser`).
      - Interact with Django ORM models representing user manifests.
      - Create, update, delete, and query Django ORM models.
      - Transform Django ORM models into Pydantic models for serialization/deserialization.

    **Parameters:**
      - `manifest`: Optional[`SAMUser`]
        The Pydantic model instance representing the manifest.
      - `pydantic_model`: Type[`SAMUser`]
        The Pydantic model class used for manifest validation.
      - `account_contact`: Optional[`AccountContact`]
        The associated account contact, if available.

    **Example Usage:**

      .. code-block:: python

         broker = SAMUserBroker()
         manifest = broker.manifest
         if manifest:
             print(manifest.apiVersion, manifest.kind)

    .. warning::

       If the manifest loader or manifest metadata is missing, the manifest may not be initialized and `None` may be returned.

    .. seealso::

       - `SAMUser` (Pydantic model)
       - Django ORM models: `User`, `AccountContact`, `UserProfile`

    .. todo::

       Make the maximum results for list operations configurable via `smarter_settings`.

    """

    # override the base abstract manifest model with the User model
    _manifest: Optional[SAMUser] = None
    _pydantic_model: Type[SAMUser] = SAMUser
    _account_contact: Optional[AccountContact] = None

    @property
    def account_contact(self) -> Optional[AccountContact]:
        """
        Retrieve the `AccountContact` associated with the current authenticated user and account.

        :returns: An `AccountContact` instance if found, otherwise `None`.

        .. note::

           - This property returns `None` if the user is not set or not authenticated.
           - If no matching `AccountContact` exists for the user's email and account, `None` is returned.


        **Example usage:**

        .. code-block:: python

           contact = broker.account_contact
           if contact:
               print(contact.first_name, contact.last_name, contact.email)

        See Also:

           - :class:`smarter.apps.account.models.AccountContact`
           - :class:`smarter.apps.account.models.User`
           - :class:`smarter.apps.account.models.Account`
        """
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
    def username(self) -> Optional[str]:
        """
        Return the username of the current user, if available.

        :returns: The username as a string, or `None` if the user is not set.

        **Example usage:**

        .. code-block:: python

           username = broker.username
           if username:
               print(f"Current user: {username}")

        See Also:

           - :class:`smarter.apps.account.models.User`
        """
        return self.user.username if self.user else None

    def manifest_to_django_orm(self) -> dict:
        """
        Convert the Smarter API User manifest (Pydantic model) into a dictionary suitable for Django ORM operations.

        :returns: A dictionary with keys and values formatted for Django ORM model assignment.

        .. note::

           Field names are automatically converted from camelCase to snake_case to match Django conventions.

        .. attention::

           The returned dictionary may include fields that are not editable in the Django ORM model. Ensure you filter out read-only fields before saving.


        **Example usage:**

        .. code-block:: python

           orm_data = broker.manifest_to_django_orm()
           for key, value in orm_data.items():
               setattr(user, key, value)
           user.save()

        See Also:

           - :meth:`django_orm_to_manifest_dict`
           - :class:`smarter.apps.account.models.User`

        """
        config_dump = self.manifest.spec.config.model_dump()  # type: ignore[return-value]
        config_dump = self.camel_to_snake(config_dump)
        return config_dump  # type: ignore[return-value]

    def django_orm_to_manifest_dict(self) -> Optional[dict]:
        """
        Convert a Django ORM `User` model instance into a dictionary formatted for Pydantic manifest consumption.

        :returns: A dictionary representing the Smarter API User manifest, or `None` if the user is not set.

        .. note::

           Field names are automatically converted from snake_case to camelCase for compatibility with Pydantic models.

        :raises: :class:`SAMUserBrokerError` if `self.user` is not set.

        **Example usage:**

        .. code-block:: python

           manifest_dict = broker.django_orm_to_manifest_dict()
           if manifest_dict:
               print(manifest_dict["spec"]["config"]["email"])

        See Also:

           - :meth:`manifest_to_django_orm`
           - :class:`SAMUser`
           - :class:`smarter.apps.account.models.User`
           - :class:`smarter.lib.manifest.enum.SamKeys`
           - :class:`smarter.lib.manifest.enumSAMMetadataKeys`
           - :class:`smarter.lib.manifest.enumSAMUserSpecKeys`

        """
        if not self.user:
            raise SAMUserBrokerError("User is not set", thing=self.kind)
        user_dict = model_to_dict(self.user)
        user_dict = self.snake_to_camel(user_dict)
        user_dict.pop("id")  # type: ignore[assignment]

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
        Return a formatted class name string for logging and diagnostics.

        :returns: A string representing the fully qualified class name, including the parent class.

        **Example usage:**

        .. code-block:: python

           logger.info(broker.formatted_class_name)

        """
        parent_class = super().formatted_class_name
        return f"{parent_class}.SAMUserBroker()"

    @property
    def kind(self) -> str:
        """
        Return the manifest kind string for the Smarter API User.

        :returns: The manifest kind as a string (e.g., ``"User"``).

        **Example usage:**

        .. code-block:: python

           if broker.kind == "User":
               print("This broker handles User manifests.")

        """
        return MANIFEST_KIND

    @property
    def manifest(self) -> Optional[SAMUser]:
        """
        Get the manifest for the Smarter API User as a Pydantic model.

        :returns: A `SAMUser` Pydantic model instance representing the Smarter API User manifest, or None if not initialized.

        .. note::

           The top-level manifest model (`SAMUser`) must be explicitly initialized with manifest data, typically using ``**data`` from the manifest loader.

        .. warning::

           If the manifest loader or manifest metadata is missing, the manifest will not be initialized and None may be returned.

        **Example usage**::

            # Access the manifest property
            manifest = broker.manifest
            if manifest:
                print(manifest.apiVersion, manifest.kind)
        """
        if self._manifest:
            return self._manifest
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMUser(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=SAMUserMetadata(**self.loader.manifest_metadata),
                spec=SAMUserSpec(**self.loader.manifest_spec),
            )
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def model_class(self) -> Type[User]:
        """
        Return the model class associated with the Smarter API User.

        :returns: The `User` model class.

        **Example usage:**

        .. code-block:: python

           model_cls = broker.model_class
           user_instance = model_cls.objects.get(username="example_user")

        .. seealso::

           - :class:`smarter.apps.account.models.User`
        """
        return User

    def example_manifest(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return the Django model class associated with the Smarter API User manifest.

        :returns: The Django `User` model class.

        **Example usage:**

        .. code-block:: python

           user_cls = broker.model_class
           user = user_cls.objects.get(username="example_user")

        .. seealso::

           - :class:`smarter.apps.account.models.User`
           - :meth:`manifest_to_django_orm`
           - :meth:`django_orm_to_manifest_dict`
           - :class:`smarter.apps.SamKeys`
           - :class:`SAMMetadataKeys`
           - :class:`SAMUserSpecKeys`

        """
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

    def get(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve Smarter API User manifests as a list of serialized Pydantic models.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including optional filter parameters.

        :returns: A `SmarterJournaledJsonResponse` containing a list of user manifests and metadata.

        .. note::

           If a username is provided in `kwargs`, only manifests for that user are returned; otherwise, all manifests for the account are listed.

        :raises: :class:`SAMUserBrokerError`
           If serialization fails for any user

        **Example usage:**

        .. code-block:: python

           response = broker.get(request, name="alice")
           print(response.data["spec"]["items"])

        See Also:

           - :class:`smarter.apps.account.serializers.UserSerializer`
           - :meth:`django_orm_to_manifest_dict`
           - :class:`smarter.lib.manifest.response.SmarterJournaledJsonResponse`
           - :class:`smarter.lib.manifest.enum.SamKeys`
           - :class:`smarter.lib.manifest.enum.SAMMetadataKeys`
           - :class:`smarter.lib.manifest.enum.SCLIResponseGet`
           - :class:`smarter.lib.manifest.enum.SCLIResponseGetData`

        """
        command = self.get.__name__
        command = SmarterJournalCliCommands(command)
        name: Optional[str] = kwargs.get(SAMMetadataKeys.NAME.value, None)
        data = []

        if name:
            user_profiles = UserProfile.objects.filter(account=self.account, user__username=name)
        else:
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

    def apply(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest data to the Django ORM `User` model and persist changes to the database.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A `SmarterJournaledJsonResponse` containing the updated user manifest.

        .. note::

           This method first calls ``super().apply()`` to ensure the manifest is loaded and validated before applying changes.

        .. attention::

           Fields in the manifest that are not editable (e.g., ``id``, ``date_joined``, ``last_login``, ``username``, ``is_superuser``) are removed before saving to the ORM model.

        :raises: :class:`SAMUserBrokerError`
           If the user instance is not set or is invalid


        **Example usage:**

        .. code-block:: python

           response = broker.apply(request)
           print(response.data)

        See Also:

           - :meth:`manifest_to_django_orm`
           - :class:`smarter.apps.account.models.User`
           - :class:`SAMUserBrokerError`

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
            if not isinstance(self.user, User):
                raise SAMUserBrokerError("User is not set", thing=self.kind, command=command)
            self.user.save()
        except Exception as e:
            raise SAMUserBrokerError(
                f"Failed to apply {self.kind} {self.user.email if isinstance(self.user, User) else None}",
                thing=self.kind,
                command=command,
            ) from e
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """

        .. attention::

            this is not implemented for the Smarter API User manifest.

        :raises: :class:`SAMBrokerErrorNotImplemented`
            Always raised to indicate that the chat operation is not implemented for this manifest type.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: Never returns; always raises an exception.
        """
        command = self.chat.__name__
        command = SmarterJournalCliCommands(command)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Describe the Smarter API User manifest by retrieving the corresponding Django ORM `User` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including the username to describe.

        :returns: A `SmarterJournaledJsonResponse` containing the user manifest data.

        :raises: :class:`SAMBrokerErrorNotFound`
           If the user with the specified username does not exist or is not associated with the account.
        :raises: :class:`SAMUserBrokerError`
           If serialization fails for the user.

        """
        command = self.describe.__name__
        command = SmarterJournalCliCommands(command)

        try:
            self._user = User.objects.get(username=self.username)
        except User.DoesNotExist as e:
            raise SAMBrokerErrorNotFound(
                f"Failed to describe {self.kind} {self.username}. Not found", thing=self.kind, command=command
            ) from e

        try:
            self._user_profile = get_cached_user_profile(user=self._user, account=self.account)
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

    def delete(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Delete the Smarter API User manifest by removing the corresponding Django ORM `User` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments, including the username to delete.

        :returns: A `SmarterJournaledJsonResponse` indicating the result of the delete operation.

        :raises: :class:`SAMBrokerErrorNotFound`
           If the user with the specified username does not exist.
        :raises: :class:`SAMUserBrokerError`
           If deletion fails for the user.

        """
        command = self.delete.__name__
        command = SmarterJournalCliCommands(command)

        if not isinstance(self.params, dict):
            raise SAMBrokerErrorNotImplemented(message="Params must be a dictionary", thing=self.kind, command=command)
        username = self.params.get("username")
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist as e:
            raise SAMBrokerErrorNotFound(
                f"Failed to delete {self.kind} {username}. Not found", thing=self.kind, command=command
            ) from e

        if user:
            try:
                user.delete()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Failed to delete {self.kind} {user.email}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def deploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Deploy the Smarter API User manifest by activating the corresponding Django ORM `User` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises: :class:`SAMUserBrokerError`
           If deployment fails for the user.

        :returns: A `SmarterJournaledJsonResponse` indicating the result of the deploy operation.
        """
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

    def undeploy(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Undeploy the Smarter API User manifest by deactivating the corresponding Django ORM `User` model instance.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :raises: :class:`SAMUserBrokerError`
           If undeployment fails for the user.
        """
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

    def logs(self, request: HttpRequest, *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs related to the Smarter API User manifest.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A `SmarterJournaledJsonResponse` containing log data.
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        data = {}
        return self.json_response_ok(command=command, data=data)
