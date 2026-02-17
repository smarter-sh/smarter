# pylint: disable=W0718
"""Smarter API User Manifest handler"""

import logging
from typing import TYPE_CHECKING, Any, Optional, Type

from django.core import serializers
from django.db import transaction

from smarter.apps.account.manifest.models.user.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.user.metadata import SAMUserMetadata
from smarter.apps.account.manifest.models.user.model import SAMUser
from smarter.apps.account.manifest.models.user.spec import (
    SAMUserSpec,
    SAMUserSpecConfig,
)
from smarter.apps.account.manifest.models.user.status import SAMUserStatus
from smarter.apps.account.models import AccountContact, User, UserProfile
from smarter.apps.account.serializers import UserSerializer
from smarter.apps.account.signals import broker_ready
from smarter.apps.account.utils import (
    cache_invalidate,
    get_cached_smarter_admin_user_profile,
    get_cached_user_profile,
)
from smarter.lib import json
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

if TYPE_CHECKING:
    from django.http import HttpRequest


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and waffle.switch_is_active(
        SmarterWaffleSwitches.MANIFEST_LOGGING
    )


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
    _brokered_user: Optional[User] = None
    _brokered_user_profile: Optional[UserProfile] = None
    _orm_instance: Optional[User] = None

    def __init__(self, *args, **kwargs):
        """
        Initialize the SAMUserBroker instance.

        This constructor initializes the broker by calling the parent class's
        constructor, which will attempt to bootstrap the class instance
        with any combination of raw manifest data (in JSON or YAML format),
        a manifest loader, or existing Django ORM models. If a manifest
        loader is provided and its kind matches the expected kind for this broker,
        the manifest is initialized using the loader's data.

        This class can bootstrap itself in any of the following ways:

        - request.body (yaml or json string)
        - name + account (determined via authentication of the request object)
        - SAMLoader instance
        - manifest instance
        - filepath to a manifest file

        If raw manifest data is provided, whether as a string or a dictionary,
        or a SAMLoader instance, the base class constructor will only goes as
        far as initializing the loader. The actual manifest model initialization
        is deferred to this constructor, which checks the loader's kind.

        :param args: Positional arguments passed to the parent constructor.
        :param kwargs: Keyword arguments passed to the parent constructor.

        **Example:**

        .. code-block:: python

            broker = SAMUserBroker(loader=loader, plugin_meta=plugin_meta)
        """
        super().__init__(*args, **kwargs)
        if not self.ready:
            if not self.loader and not self.manifest and not self.brokered_user:
                logger.warning(
                    "%s.__init__() No loader nor existing User provided for %s broker. Cannot initialize.",
                    self.formatted_class_name,
                    self.kind,
                )
                return
            if self.loader and self.loader.manifest_kind != self.kind:
                raise SAMBrokerErrorNotReady(
                    f"Loader manifest kind {self.loader.manifest_kind} does not match broker kind {self.kind}",
                    thing=self.kind,
                )

        msg = f"{self.formatted_class_name}.__init__() broker for {self.kind} {self.name} is {self.ready_state}."
        if self.ready:
            logger.info(msg)
        else:
            logger.warning(msg)

    @property
    def ready(self) -> bool:
        """
        Check if the broker is ready for operations.

        This property determines whether the broker has been properly initialized
        and is ready to perform its functions. A broker is considered ready if
        it has a valid manifest loaded, either from raw data, a loader, or
        existing Django ORM models.

        :returns: ``True`` if the broker is ready, ``False`` otherwise.
        :rtype: bool
        """
        retval = super().ready
        if not retval:
            logger.warning("%s.ready() AbstractBroker is not ready for %s", self.formatted_class_name, self.kind)
            return False
        retval = self.manifest is not None or self.brokered_user is not None
        logger.debug(
            "%s.ready() manifest presence indicates ready=%s for %s",
            self.formatted_class_name,
            retval,
            self.kind,
        )
        if retval:
            broker_ready.send(sender=self.__class__, broker=self)
        return retval

    @property
    def brokered_user(self) -> Optional[User]:
        """
        In order to disambiguate between the AccountMixin.user
        (the authenticated user making the request) and the User
        resource being brokered, we use the term "brokered_user".

        Retrieve the `User` model instance associated with the current broker.

        :returns: A `User` instance if found, otherwise `None`.

        .. note::

           - This property returns `None` if the user is not set.
           - If no matching `User` exists for the broker's username, `None` is returned.

        **Example usage:**

        .. code-block:: python

            user = broker.brokered_user
            if user:
                print(user.first_name, user.last_name, user.email)

        See Also:
              - :class:`smarter.apps.account.models.User`
        """
        if self._brokered_user:
            return self._brokered_user
        if self.name is None:
            logger.debug(
                "%s.brokered_user() brokered user name is not set. Cannot retrieve User.",
                self.formatted_class_name,
            )
            return None
        try:
            self._brokered_user = User.objects.get(username=self._name)
            logger.debug(
                "%s.brokered_user() initialized existing User: %s",
                self.formatted_class_name,
                self.name,
            )
        except User.DoesNotExist:
            logger.debug(
                "%s.brokered_user() User does not exist: %s",
                self.formatted_class_name,
                self.name,
            )
        return self._brokered_user

    @brokered_user.setter
    def brokered_user(self, value: User) -> None:
        """
        Set the `User` model instance for the current broker.

        :param value: A `User` instance to associate with the broker.

          Example usage:

          .. code-block:: python
              broker.brokered_user = user_instance

          See Also:
              - :class:`smarter.apps.account.models.User`
        """
        self._brokered_user = value
        logger.debug(
            "%s.brokered_user() set User: %s",
            self.formatted_class_name,
            value,
        )

    @property
    def brokered_user_profile(self) -> Optional[UserProfile]:
        """
        The UserProfile associated with the brokered user. This disambiguates
        between the AccountMixin.user_profile (the profile of the authenticated
        user making the request) and the UserProfile resource being brokered.

        Retrieve the `UserProfile` model instance associated with the current brokered user.

        :returns: A `UserProfile` instance if found, otherwise `None`.

        .. note::

           - This property returns `None` if the brokered user is not set.
           - If no matching `UserProfile` exists for the brokered user and account, `None` is returned.

        **Example usage:**

        .. code-block:: python

              profile = broker.brokered_user_profile
                if profile:
                    print(profile.name, profile.description)

        See Also:
              - :class:`smarter.apps.account.models.UserProfile`
        """
        if self._brokered_user_profile:
            return self._brokered_user_profile
        if not self._brokered_user:
            logger.debug(
                "%s.brokered_user_profile() brokered user is not set. Cannot retrieve UserProfile.",
                self.formatted_class_name,
            )
            return None

        try:
            self._brokered_user_profile = get_cached_user_profile(user=self.brokered_user, account=self.account)  # type: ignore
            logger.debug(
                "%s.brokered_user_profile() initialized existing UserProfile: %s",
                self.formatted_class_name,
                self._brokered_user_profile,
            )
        except UserProfile.DoesNotExist:
            logger.warning(
                "%s.brokered_user_profile() UserProfile does not exist for user: %s and account: %s",
                self.formatted_class_name,
                self.brokered_user,
                self.account,
            )
        return self._brokered_user_profile

    @brokered_user_profile.setter
    def brokered_user_profile(self, value: UserProfile) -> None:
        """
        Set the `UserProfile` model instance for the current brokered user.

        :param value: A `UserProfile` instance to associate with the brokered user.

        **Example usage:**

        .. code-block:: python

              broker.brokered_user_profile = profile_instance

        See Also:

           - :class:`smarter.apps.account.models.UserProfile`
        """
        self._brokered_user_profile = value
        logger.debug(
            "%s.brokered_user_profile() set UserProfile: %s",
            self.formatted_class_name,
            value,
        )
        self._brokered_user = value.user
        logger.debug(
            "%s.brokered_user_profile() set brokered User: %s from UserProfile",
            self.formatted_class_name,
            value.user,
        )

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
        if not self.brokered_user:
            return None
        if not self.brokered_user.is_authenticated:
            return None
        try:
            self._account_contact = AccountContact.objects.get(account=self.account, email=self.brokered_user.email)
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
        return self.brokered_user.username if self.brokered_user else None

    @property
    def SerializerClass(self) -> Type[UserSerializer]:
        """
        Return the serializer class associated with the Smarter API User.

        :returns: The `UserSerializer` class.

        **Example usage:**

        .. code-block:: python

           serializer_cls = broker.SerializerClass
           serializer = serializer_cls(instance=user_instance)

        .. seealso::

           - :class:`smarter.apps.account.serializers.UserSerializer`
        """
        return UserSerializer

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
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.camel_to_snake(config_dump)
        if not isinstance(config_dump, dict):
            config_dump = json.loads(json.dumps(config_dump))
        return config_dump

    def django_orm_to_manifest_dict(self) -> Optional[dict[str, Any]]:
        """
        Convert a Django ORM `User` model instance into a dictionary formatted for Pydantic manifest consumption.

        :returns: A dictionary representing the Smarter API User manifest, or `None` if the user is not set.

        .. note::

           Field names are automatically converted from snake_case to camelCase for compatibility with Pydantic models.

        :raises: :class:`SAMUserBrokerError` if `self.brokered_user` is not set.

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
        if not self.manifest:
            raise SAMUserBrokerError("User manifest is not set", thing=self.kind)

        return self.manifest.model_dump()

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
        return f"{parent_class}.{SAMUserBroker.__name__}[{id(self)}]"

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
    def name(self) -> Optional[str]:
        """
        Get the name of the Smarter API Account.

        :returns: The name of the Smarter API Account, or None if not set.
        :rtype: Optional[str]
        """
        retval = super().name
        if retval:
            return retval
        if self._brokered_user:
            return str(self._brokered_user.username)

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
            if not isinstance(self._manifest, SAMUser):
                raise SAMUserBrokerError(
                    message=f"Invalid manifest type for {self.kind} broker: {type(self._manifest)}",
                    thing=self.kind,
                    command=SmarterJournalCliCommands.APPLY,
                )
            return self._manifest
        if not self.account:
            logger.warning("%s.manifest called with no account", self.formatted_class_name)
            return None
        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_kind == self.kind:
            metadata = SAMUserMetadata(**self.loader.manifest_metadata)
            spec = SAMUserSpec(**self.loader.manifest_spec)
            self._manifest = SAMUser(
                apiVersion=self.loader.manifest_api_version,
                kind=self.loader.manifest_kind,
                metadata=metadata,
                spec=spec,
            )
        # 2.) next, (and only if a loader is not available) try to initialize
        #     from existing Account model if available
        elif self.brokered_user:
            self._manifest = SAMUser(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=SAMUserMetadata(
                    name=self.brokered_user.username,
                    description=self.brokered_user_profile.description or "no description",
                    version=self.brokered_user_profile.version,
                    username=self.brokered_user_profile.user.username,
                    tags=self.brokered_user_profile.tags.names(),
                    annotations=self.brokered_user_profile.annotations,
                ),
                spec=SAMUserSpec(
                    config=SAMUserSpecConfig(
                        firstName=self.brokered_user.first_name,
                        lastName=self.brokered_user.last_name,
                        email=self.brokered_user.email,
                        isStaff=self.brokered_user.is_staff,
                        isActive=self.brokered_user.is_active,
                    )
                ),
                status=SAMUserStatus(
                    account_number=self.account.account_number,
                    username=self.brokered_user.username,
                    created=self.brokered_user.date_joined,
                    modified=self.brokered_user.last_login or self.brokered_user.date_joined,
                ),
            )
            return self._manifest
        if not self._manifest:
            logger.warning("%s.manifest could not be initialized", self.formatted_class_name)
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def ORMModelClass(self) -> Type[User]:
        """
        Return the model class associated with the Smarter API User.

        :returns: The `User` model class.

        **Example usage:**

        .. code-block:: python

           model_cls = broker.ORMModelClass
           user_instance = model_cls.objects.get(username="example_user")

        .. seealso::

           - :class:`smarter.apps.account.models.User`
        """
        return User

    @property
    def orm_instance(self) -> Optional[User]:
        """
        Return the Django ORM model instance for the broker.

        :return: The Django ORM model instance for the broker.
        :rtype: Optional[TimestampedModel]
        """
        if self._orm_instance:
            return self._orm_instance

        if not self.ready:
            logger.warning(
                "%s.orm_instance() - broker is not ready. Cannot retrieve ORM instance.",
                self.abstract_broker_logger_prefix,
            )
            return None
        try:
            logger.debug(
                "%s.orm_instance() - attempting to retrieve ORM instance %s for user=%s, name=%s",
                self.abstract_broker_logger_prefix,
                User.__name__,
                self.user,
                self.name,
            )
            instance = User.objects.get(username=self.name)
            logger.debug(
                "%s.orm_instance() - retrieved ORM instance: %s",
                self.abstract_broker_logger_prefix,
                serializers.serialize("json", [instance]),
            )
            return instance
        except User.DoesNotExist:
            logger.warning(
                "%s.orm_instance() - ORM instance does not exist for account=%s, name=%s",
                self.abstract_broker_logger_prefix,
                self.account,
                self.name,
            )
            return None

    @property
    def SAMModelClass(self) -> Type[SAMUser]:
        """
        Return the Pydantic model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[SAMUser]
        """
        return SAMUser

    def example_manifest(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return the SAM `User` model associated with the Smarter API User manifest.

        :returns: a dict representing the SAM `User` model.

        .. seealso::

           - :class:`smarter.apps.account.models.User`
           - :meth:`django_orm_to_manifest_dict`

        """
        command = self.example_manifest.__name__
        command = SmarterJournalCliCommands(command)
        logger.debug("%s.example_manifest() called", self.formatted_class_name)
        smarter_admin_profile = get_cached_smarter_admin_user_profile()
        self.brokered_user = smarter_admin_profile.user
        self.brokered_user_profile = smarter_admin_profile
        data = self.django_orm_to_manifest_dict()
        return self.json_response_ok(command=command, data=data)

    def get(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        logger.debug("%s.get() called", self.formatted_class_name)
        name: Optional[str] = kwargs.get(SAMMetadataKeys.NAME.value, None)
        data = []

        if name:
            user_profiles = UserProfile.objects.filter(account=self.account, user__username=name)
        else:
            user_profiles = UserProfile.objects.filter(account=self.account)
        users = [user_profile.user for user_profile in user_profiles]

        model_titles = self.get_model_titles(serializer=UserSerializer())

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for user in users:
            try:
                self.brokered_user = user
                model_dump = UserSerializer(user).data
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
                SCLIResponseGetData.TITLES.value: model_titles,
                SCLIResponseGetData.ITEMS.value: data,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def apply(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        logger.debug("%s.apply() called", self.formatted_class_name)
        readonly_fields = ["id", "date_joined", "last_login", "username", "is_superuser"]

        if not self.user.is_staff:
            raise SAMUserBrokerError(
                message="Only account admins can apply user manifests.",
                thing=self.kind,
                command=command,
            )

        if not self.manifest:
            raise SAMUserBrokerError("User manifest is not set", thing=self.kind, command=command)

        try:
            with transaction.atomic():
                if not self.brokered_user:
                    self.brokered_user = User(
                        username=self.manifest.metadata.username,
                        is_superuser=False,
                    )
                    logger.debug(
                        "%s.apply() Created new (unsaved) User instance for %s", self.formatted_class_name, self.kind
                    )
                if not self.brokered_user_profile:
                    self.brokered_user_profile = UserProfile(
                        account=self.account,
                        user=self.brokered_user,
                        name=self.manifest.metadata.name,
                    )
                    logger.debug(
                        "%s.apply() Created new (unsaved) UserProfile instance for %s",
                        self.formatted_class_name,
                        self.kind,
                    )

                # User model
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
                    setattr(self.brokered_user, key, value)
                    logger.debug("%s.apply() Setting %s to %s", self.formatted_class_name, key, value)

                # UserProfile model
                self.brokered_user_profile.description = self.manifest.metadata.description
                self.brokered_user_profile.version = self.manifest.metadata.version
                # Convert tags to set for TaggableManager compatibility
                tags = set(self.manifest.metadata.tags) if self.manifest.metadata.tags else set()
                self.brokered_user_profile.tags = tags
                self.brokered_user_profile.annotations = self.manifest.metadata.annotations

                self.brokered_user.save()
                self.brokered_user.refresh_from_db()
                self.brokered_user_profile.save()
                self.brokered_user_profile.refresh_from_db()
                cache_invalidate(user=self.brokered_user, account=self.account)  # type: ignore
        # pylint: disable=broad-except
        except Exception as e:
            raise SAMUserBrokerError(
                f"Failed to apply {self.kind} {self.brokered_user.email if isinstance(self.brokered_user, User) else None}",
                thing=self.kind,
                command=command,
            ) from e
        return self.json_response_ok(command=command, data=self.to_json())

    def chat(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        logger.debug("%s.chat() called", self.formatted_class_name)
        raise SAMBrokerErrorNotImplemented(message="Chat not implemented", thing=self.kind, command=command)

    def describe(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        logger.debug("%s.describe() called", self.formatted_class_name)

        if not self.brokered_user:
            raise SAMBrokerErrorNotFound(f"Failed to describe {self.kind}. Not found", thing=self.kind, command=command)

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

        if self.brokered_user:
            try:
                data = self.manifest.model_dump()
                return self.json_response_ok(command=command, data=data)
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Failed to describe {self.kind} {self.brokered_user.email}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def delete(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        logger.debug("%s.delete() called", self.formatted_class_name)

        if not self.user.is_staff:
            raise SAMUserBrokerError(
                message="Only account admins can delete user manifests.",
                thing=self.kind,
                command=command,
            )

        if not self.brokered_user:
            raise SAMBrokerErrorNotFound(f"Failed to delete {self.kind}. Not found", thing=self.kind, command=command)

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

    def deploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        logger.debug("%s.deploy() called", self.formatted_class_name)

        if not self.user.is_staff:
            raise SAMUserBrokerError(
                message="Only account admins can deploy user manifests.",
                thing=self.kind,
                command=command,
            )

        if self.brokered_user:
            try:
                if not self.brokered_user.is_active:
                    self.brokered_user.is_active = True
                    self.brokered_user.save()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Failed to deploy {self.kind} {self.brokered_user.email}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def undeploy(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
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
        logger.debug("%s.undeploy() called", self.formatted_class_name)

        if not self.user.is_staff:
            raise SAMUserBrokerError(
                message="Only account admins can undeploy user manifests.",
                thing=self.kind,
                command=command,
            )

        if self.brokered_user:
            try:
                if self.brokered_user.is_active:
                    self.brokered_user.is_active = False
                    self.brokered_user.save()
                return self.json_response_ok(command=command, data={})
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Failed to deploy {self.kind} {self.brokered_user.email}", thing=self.kind, command=command
                ) from e
        raise SAMBrokerErrorNotReady(f"{self.kind} not ready", thing=self.kind, command=command)

    def logs(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Retrieve logs related to the Smarter API User manifest.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A `SmarterJournaledJsonResponse` containing log data.
        """
        command = self.logs.__name__
        command = SmarterJournalCliCommands(command)
        logger.debug("%s.logs() called", self.formatted_class_name)

        data = {}
        return self.json_response_ok(command=command, data=data)
