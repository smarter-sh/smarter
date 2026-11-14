# pylint: disable=W0718,C0302
"""Smarter API User Manifest handler."""

import datetime
from typing import TYPE_CHECKING, List, Optional, Type

from django.core import serializers
from django.db import transaction

from smarter.apps.account.manifest.models.user.const import MANIFEST_KIND
from smarter.apps.account.manifest.models.user.metadata import SAMUserMetadata
from smarter.apps.account.manifest.models.user.model import SAMUser
from smarter.apps.account.manifest.models.user.spec import (
    SAMUserAccountMembership,
    SAMUserSpec,
    SAMUserSpecConfig,
)
from smarter.apps.account.manifest.models.user.status import SAMUserStatus
from smarter.apps.account.models import (
    Account,
    AccountContact,
    User,
    UserProfile,
    user_administers_account,
)
from smarter.apps.account.serializers import UserSerializer
from smarter.common.utils.decorators import camel_case
from smarter.lib import json, logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.journal.enum import SmarterJournalCliCommands
from smarter.lib.journal.http import SmarterJournaledJsonResponse
from smarter.lib.manifest.broker import (
    AbstractBroker,
    SAMBrokerError,
    SAMBrokerErrorNotFound,
    SAMBrokerErrorNotImplemented,
    SAMBrokerErrorNotReady,
    SAMDependency,
    SAMDependents,
    memoized_dependencies,
)
from smarter.lib.manifest.enum import (
    SAMKeys,
    SAMMetadataKeys,
    SCLIResponseGet,
    SCLIResponseGetData,
)
from smarter.lib.typing import SmarterDictType, required

if TYPE_CHECKING:
    from django.http import HttpRequest


logger = logging.getSmarterLogger(
    __name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_LOGGING, SmarterWaffleSwitches.MANIFEST_LOGGING]
)

#: The User fields that log messages may show. Not ``password``, the password's hash.
LOGGED_FIELDS = (
    "username",
    "email",
    "first_name",
    "last_name",
    "is_active",
    "is_staff",
    "is_superuser",
    "last_login",
    "date_joined",
)

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
        """The label of this error, used in its string form."""
        return "Smarter API User Manifest Broker Error"


class SAMUserBroker(AbstractBroker[User, User]):
    """
    Smarter API User Manifest Broker.

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
    deployable = True
    _account_contact: Optional[AccountContact] = None
    _brokered_user: Optional[User] = None
    _brokered_user_profile: Optional[UserProfile] = None
    _orm_instance: Optional[User] = None
    _orm_meta_instance: Optional[User] = None

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        logger.debug(
            "%s.__init__() broker for %s %s is %s.", self.formatted_class_name, self.kind, self.name, self.ready_state
        )

    @property
    def brokered_user(self) -> Optional[User]:
        """
        In order to disambiguate between the AccountMixin.user.

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
    def brokered_user(self, value: Optional[User]) -> None:
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
        The UserProfile associated with the brokered user.

        This disambiguates
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
            self._brokered_user_profile = UserProfile.get_cached_object(user=self.brokered_user, account=self.account)  # type: ignore
            logger.debug(
                "%s.brokered_user_profile() initialized existing UserProfile: %s",
                self.formatted_class_name,
                self._brokered_user_profile,
            )
        except UserProfile.DoesNotExist:
            # a superuser sees a user of any account, e.g. one whose User manifest lists only an organization's
            # departments, and not the account of the superuser who applied it.
            if isinstance(self.user, User) and self.user.is_superuser:
                profiles = UserProfile.objects.filter(user=self.brokered_user).order_by("pk")
                self._brokered_user_profile = profiles.first()
            if self._brokered_user_profile is None:
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

    def manifest_to_django_orm(self) -> SmarterDictType:
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
        if not isinstance(self.manifest, SAMUser):
            raise SAMUserBrokerError(
                message=f"Manifest must be of type {SAMUser.__name__} to convert to Django ORM, got {type(self.manifest)}: {self.manifest}",
                thing=self.kind,
                command=SmarterJournalCliCommands.APPLY,
            )
        metadata = super().manifest_to_django_orm()
        config_dump = self.manifest.spec.config.model_dump()
        config_dump = self.to_snake_case(config_dump)
        if not isinstance(config_dump, dict):
            config_dump = json.loads(json.dumps(config_dump))
        retval = {**metadata, **config_dump}
        logger.debug(
            "%s.manifest_to_django_orm() Converted manifest to Django ORM dictionary for %s: %s",
            self.formatted_class_name,
            self.kind,
            retval,
        )
        return retval

    @camel_case()
    def django_orm_to_manifest_dict(self) -> Optional[SmarterDictType]:
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

        retval = self.manifest.model_dump()
        logger.debug(
            "%s.django_orm_to_manifest_dict() Converted Django ORM User instance to manifest dictionary for %s: %s",
            self.formatted_class_name,
            self.kind,
            retval,
        )
        return retval

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
        this_class = f".{SAMUserBroker.__name__}[{id(self)}]"
        return f"{parent_class}{self.formatted_text(this_class)}"

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
        return None

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
        # an unauthenticated request, e.g. for the example manifest, has no account, but may have a brokered user.
        if not self.account and not self.brokered_user:
            logger.warning("%s.manifest called with no account", self.formatted_class_name)
            return None
        # 1.) prioritize manifest loader data if available. if it was provided
        #     in the request body then this is the authoritative source.
        if self.loader and self.loader.manifest_kind == self.kind:
            self._manifest = SAMUser.model_validate(self.loader.manifest_sections)
        # 2.) next, (and only if a loader is not available) try to initialize
        #     from existing Account model if available
        elif self.brokered_user:
            if not isinstance(self.brokered_user_profile, UserProfile):
                raise SAMUserBrokerError(
                    message="Brokered user profile is not properly initialized. Cannot initialize manifest.",
                    thing=self.kind,
                    command=SmarterJournalCliCommands.APPLY,
                )
            self._manifest = SAMUser(
                apiVersion=self.api_version,
                kind=self.kind,
                metadata=SAMUserMetadata(
                    name=self.brokered_user.username,
                    description=self.brokered_user_profile.description or "no description",
                    version=self.brokered_user_profile.version,
                    username=self.brokered_user_profile.user.username,
                    tags=self.brokered_user_profile.tags_list,
                    annotations=self.brokered_user_profile.annotations,
                ),
                spec=SAMUserSpec(
                    config=SAMUserSpecConfig(
                        firstName=self.brokered_user.first_name,
                        lastName=self.brokered_user.last_name,
                        email=self.brokered_user.email,
                        isStaff=self.brokered_user.is_staff,
                        isActive=self.brokered_user.is_active,
                    ),
                    accounts=self.memberships_for_manifest(),
                ),
                status=SAMUserStatus(
                    # the brokered user's account, which is not necessarily the requester's.
                    account_number=required(
                        self.brokered_user_profile.account.account_number, "user_profile.account.account_number"
                    ),
                    recordLocator=f"user-{self.brokered_user.id}-###-###-###",  # type: ignore
                    username=self.brokered_user.username,
                    created=self.brokered_user.date_joined,
                    modified=self.brokered_user.last_login or self.brokered_user.date_joined,
                ),
            )
            return self._manifest
        if not self._manifest:
            logger.debug("%s.manifest could not be initialized", self.formatted_class_name)
        return self._manifest

    ###########################################################################
    # Smarter manifest abstract method implementations
    ###########################################################################
    @property
    def ORMMetaModelClass(self) -> Type[User]:
        """
        Return the Django ORM meta model class for the broker.

        :return: The Django ORM meta model class definition for the broker.
        :rtype: Type[User]
        """
        return User

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

        try:
            logger.debug(
                "%s.orm_instance() - attempting to retrieve %s instance for user=%s, name=%s",
                self.formatted_class_name,
                User.__name__,
                self.user,
                self.name,
            )
            self._orm_instance = User.objects.get(username=self.name)
            logger.debug(
                "%s.orm_instance() - retrieved %s instance: %s",
                self.formatted_class_name,
                User.__name__,
                serializers.serialize("json", [self._orm_instance], fields=LOGGED_FIELDS),
            )
            return self._orm_instance
        except User.DoesNotExist:
            logger.warning(
                "%s.orm_instance() - %s instance does not exist for account=%s, name=%s",
                self.formatted_class_name,
                User.__name__,
                self.account,
                self.name,
            )
            return None

    def orm_meta_instance_setter(self) -> None:
        """Override the base method to initialize the ORM meta model instance for the broker."""
        if self._orm_instance:
            logger.debug(
                "%s.orm_meta_instance_setter() ORM instance is already set. Setting ORM meta instance to ORM instance.",
                self.formatted_class_name,
            )
            self._orm_meta_instance = self._orm_instance  # type: ignore
            return
        if not self.name:
            logger.debug(
                "%s.orm_meta_instance_setter() - name is not set. Cannot retrieve ORM meta instance for %s.",
                self.formatted_class_name,
                User.__name__,
            )
            return

        self._orm_meta_instance = None
        try:
            self._orm_meta_instance = User.objects.get(username=self.name)  # type: ignore
            logger.debug(
                "%s.orm_meta_instance_setter() - initialized %s meta: %s",
                self.formatted_class_name,
                User.__name__,
                serializers.serialize("json", [self.orm_meta_instance], fields=LOGGED_FIELDS),  # type: ignore
            )
        except User.DoesNotExist:
            logger.warning(
                "%s.orm_meta_instance_setter() - %s meta instance does not exist for %s owned by %s",
                self.formatted_class_name,
                User.__name__,
                self.name,
                self.account,
            )
        except Exception as e:
            logger.error(
                "%s.orm_meta_instance_setter() - unexpected error retrieving %s meta instance for %s owned by %s: %s",
                self.formatted_class_name,
                User.__name__,
                self.name,
                self.account,
                str(e),
            )

    @property
    def SAMModelClass(self) -> Type[SAMUser]:
        """
        Return the Pydantic model class for the broker.

        :return: The Pydantic model class definition for the broker.
        :rtype: Type[SAMUser]
        """
        return SAMUser

    def cache_invalidations(self) -> None:
        """
        Invalidate any relevant caches for the brokered user.

        Invalidates the cached UserProfile of the brokered user in each account they belong to, which with
        ``spec.accounts`` need not include the current account.
        """
        logger.debug("%s.cache_invalidations() called.", self.formatted_class_name_cache_invalidations)
        accounts = [self.account]
        if isinstance(self.brokered_user, User) and self.brokered_user.pk:
            for profile in UserProfile.objects.filter(user=self.brokered_user).select_related("account"):
                accounts.append(profile.account)
        for account in accounts:
            try:
                UserProfile.get_cached_object(invalidate=True, user=self.brokered_user, account=account)  # type: ignore
            except UserProfile.DoesNotExist:
                pass
        return super().cache_invalidations()

    def example_manifest(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Return the SAM `User` model associated with the Smarter API User manifest.

        :returns: a dict representing the SAM `User` model.

        .. seealso::

           - :class:`smarter.apps.account.models.User`
           - :meth:`django_orm_to_manifest_dict`
        """
        command = SmarterJournalCliCommands(self.example_manifest.__name__)
        logger.debug("%s.example_manifest() called", self.formatted_class_name)
        # placeholder values, rather than a description of a real user, such as the smarter admin,
        # whose email and account number would otherwise be published in the example.
        manifest = SAMUser(
            apiVersion=self.api_version,
            kind=self.kind,
            metadata=SAMUserMetadata(
                name="example_user",
                description="An example Smarter API manifest for a User",
                version="1.0.0",
                tags=["example"],
                annotations={},
                username="example_user",
            ),
            spec=SAMUserSpec(
                config=SAMUserSpecConfig(
                    firstName="Example",
                    lastName="User",
                    email="example.user@example.com",
                    isStaff=False,
                    isActive=True,
                ),
                accounts=None,
            ),
            status=SAMUserStatus(
                account_number="1234-5678-9012",
                username="example_user",
                recordLocator="user-example",
                created=datetime.datetime(2024, 1, 1, 0, 0, 0, tzinfo=datetime.timezone.utc),
                modified=datetime.datetime(2024, 1, 2, 0, 0, 0, tzinfo=datetime.timezone.utc),
            ),
        )
        return self.json_response_ok(command=command, data=manifest.model_dump())

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
        command = SmarterJournalCliCommands(self.get.__name__)
        logger.debug("%s.get() called", self.formatted_class_name)
        name: Optional[str] = kwargs.get(SAMMetadataKeys.NAME.value, None)
        items: list[SmarterDictType] = []

        if name:
            user_profiles = UserProfile.objects.filter(account=self.account, user__username=name)
        else:
            user_profiles = UserProfile.objects.filter(account=self.account)
        user_profiles = self.filter_by_annotation_selector(user_profiles, kwargs)
        users = [user_profile.cached_user for user_profile in user_profiles]

        model_titles = self.get_model_titles(serializer=UserSerializer())

        # iterate over the QuerySet and use the manifest controller to create a Pydantic model dump for each Plugin
        for user in users:
            if not isinstance(user, User):
                raise SAMUserBrokerError(
                    message=f"Expected User instance in users QuerySet, got {type(user)}: {user}",
                    thing=self.kind,
                    command=command,
                )
            try:
                self.brokered_user = user
                model_dump = UserSerializer(user).data
                camel_cased_model_dump = self.to_camel_case(model_dump)
                items.append(camel_cased_model_dump)
            except Exception as e:
                raise SAMUserBrokerError(
                    f"Model dump failed for {self.kind} {user.username}", thing=self.kind, command=command
                ) from e
        data = {
            SAMKeys.APIVERSION.value: self.api_version,
            SAMKeys.KIND.value: self.kind,
            SAMKeys.METADATA.value: {"count": len(items)},
            SCLIResponseGet.KWARGS.value: self.params,
            SCLIResponseGet.DATA.value: {
                SCLIResponseGetData.TITLES.value: model_titles,
                SCLIResponseGetData.ITEMS.value: items,
            },
        }
        return self.json_response_ok(command=command, data=data)

    def check_authority_over_memberships(self, command: SmarterJournalCliCommands) -> None:
        """
        Refuse ``spec.accounts`` that list an account which the applier doesn't administer, unless a superuser applies it.

        :param command: The command, for the error.
        :raises SAMUserBrokerError: if a listed account isn't one that the applier administers.
        """
        if self.manifest is None or self.manifest.spec.accounts is None:
            return
        if not isinstance(self.user, User):
            return
        if self.user.is_superuser:
            return
        for membership in self.manifest.spec.accounts:
            applier_profile = UserProfile.objects.filter(
                user=self.user, account__account_number=membership.accountNumber
            ).first()
            if not user_administers_account(self.user, applier_profile):
                raise SAMUserBrokerError(
                    message=f"Only an administrator of account {membership.accountNumber} may add users to it.",
                    thing=self.kind,
                    command=command,
                )

    def apply_memberships(self, brokered_user: User, memberships: list[SAMUserAccountMembership]) -> None:
        """
        Create each of the user's listed memberships that is missing, and update the others.

        A membership that the list omits is left as it is: deleting a profile deletes every resource that it owns.

        :param brokered_user: The user, saved.
        :param memberships: ``spec.accounts``.
        :raises SAMBrokerErrorNotFound: if a listed account doesn't exist.
        """
        manifest = required(self.manifest, "manifest")
        tags = set(manifest.metadata.tags) if manifest.metadata.tags else set()
        for membership in memberships:
            account = Account.objects.filter(account_number=membership.accountNumber).first()
            if account is None:
                raise SAMBrokerErrorNotFound(
                    f"Account {membership.accountNumber} does not exist.",
                    thing=self.kind,
                    command=SmarterJournalCliCommands.APPLY,
                )
            user_profile = UserProfile.objects.filter(user=brokered_user, account=account).first()
            if user_profile is None:
                user_profile = UserProfile(account=account, user=brokered_user, name=manifest.metadata.name)
            user_profile.is_account_admin = membership.isAccountAdmin
            user_profile.description = manifest.metadata.description
            user_profile.version = manifest.metadata.version
            user_profile.tags = tags
            user_profile.annotations = manifest.metadata.annotations
            user_profile.save()
            logger.debug(
                "%s.apply_memberships() user id %s belongs to account %s, administrator: %s",
                self.formatted_class_name,
                brokered_user.pk,
                membership.accountNumber,
                membership.isAccountAdmin,
            )

    def apply_own_account_profile(self, brokered_user: User) -> None:
        """
        Create or update the user's profile in the account of whoever applies the manifest, which has no ``spec.accounts``.

        :param brokered_user: The user, saved.
        """
        manifest = required(self.manifest, "manifest")
        # in this account only: brokered_user_profile may be, for a superuser, the user's profile in another one.
        brokered_user_profile = UserProfile.objects.filter(user=brokered_user, account=self.account).first()
        if not brokered_user_profile:
            brokered_user_profile = UserProfile(
                account=self.account,
                user=brokered_user,
                name=manifest.metadata.name,
            )
            self.brokered_user_profile = brokered_user_profile
            logger.debug(
                "%s.apply_own_account_profile() Created new (unsaved) UserProfile instance for %s",
                self.formatted_class_name,
                self.kind,
            )
        brokered_user_profile.description = manifest.metadata.description
        brokered_user_profile.version = manifest.metadata.version
        # Convert tags to set for TaggableManager compatibility
        tags = set(manifest.metadata.tags) if manifest.metadata.tags else set()
        brokered_user_profile.tags = tags
        brokered_user_profile.annotations = manifest.metadata.annotations
        brokered_user_profile.save()
        brokered_user_profile.refresh_from_db()

    def memberships_for_manifest(self) -> Optional[list[SAMUserAccountMembership]]:
        """
        The brokered user's memberships, for ``describe``: every one, but only for a superuser.

        Anyone else sees the user as a member of the current account only, without ``spec.accounts``, so that a
        user's other accounts aren't shown to the administrators of one of them.

        :returns: The memberships, or None.
        """
        if not isinstance(self.user, User) or not self.user.is_superuser:
            return None
        if not isinstance(self.brokered_user, User):
            return None
        profiles = UserProfile.objects.filter(user=self.brokered_user).select_related("account").order_by("pk")
        retval = []
        for profile in profiles:
            membership = SAMUserAccountMembership(
                accountNumber=str(profile.account.account_number), isAccountAdmin=profile.is_account_admin
            )
            retval.append(membership)
        return retval

    def check_authority_over_user(self, command: SmarterJournalCliCommands) -> None:
        """
        Refuse a User manifest that reaches beyond the applier's own account, unless a superuser applies it.

        A user is found by username across the whole platform. So an account administrator could otherwise change a
        user of another account, e.g. their email, or deactivate them. And ``isStaff`` sets ``User.is_staff``, which
        opens the Django admin site and administers every account the user belongs to, so an administrator of one
        account, through ``UserProfile.is_account_admin``, could otherwise make themselves staff.

        :param command: The command, for the error.
        :raises SAMUserBrokerError: if an existing user doesn't belong to the applier's account, or a user who isn't
            staff would change a user's ``is_staff``.
        """
        if not isinstance(self.user, User):
            return
        if self.user.is_superuser:
            return
        existing = self.brokered_user
        if isinstance(existing, User) and existing.pk:
            member = UserProfile.objects.filter(user=existing, account=self.account).exists()
            if not member:
                raise SAMUserBrokerError(
                    message=f"User {existing.username} belongs to another account.",
                    thing=self.kind,
                    command=command,
                )
        if self.user.is_staff:
            return
        current_is_staff = False
        if isinstance(existing, User):
            current_is_staff = existing.is_staff
        requested_is_staff = current_is_staff
        if self.manifest is not None and self.manifest.spec.config.isStaff is not None:
            requested_is_staff = bool(self.manifest.spec.config.isStaff)
        if requested_is_staff != current_is_staff:
            raise SAMUserBrokerError(
                message="Only staff may change whether a user is staff.",
                thing=self.kind,
                command=command,
            )

    def apply(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        Apply the manifest data to the Django ORM `User` model and persist changes to the database.

        .. note::

            tags are handled separately because they are of type TaggableManager and
            require a different method to set them.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: A `SmarterJournaledJsonResponse` containing the updated user manifest.

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
        command = SmarterJournalCliCommands(self.apply.__name__)
        logger.debug("%s.apply() called", self.formatted_class_name)
        readonly_fields = ["id", "date_joined", "last_login", "username", "is_superuser", "tags"]

        if not isinstance(self.user, User):
            raise SAMUserBrokerError(
                message=f"Authenticated user must be a User instance, got {type(self.user)}: {self.user}",
                thing=self.kind,
                command=command,
            )
        if not self.administers_account:
            raise SAMUserBrokerError(
                message="Only account admins can apply user manifests.",
                thing=self.kind,
                command=command,
            )

        if not self.manifest:
            raise SAMUserBrokerError("User manifest is not set", thing=self.kind, command=command)

        self.check_authority_over_user(command)
        self.check_authority_over_memberships(command)

        try:
            with transaction.atomic():
                brokered_user = self.brokered_user
                if not brokered_user:
                    brokered_user = User(
                        username=self.manifest.metadata.username,
                        is_superuser=False,
                    )
                    self.brokered_user = brokered_user
                    logger.debug(
                        "%s.apply() Created new (unsaved) User instance for %s", self.formatted_class_name, self.kind
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
                data.pop("user_profile", None)
                for key, value in data.items():
                    setattr(brokered_user, key, value)
                    logger.debug("%s.apply() Setting %s to %s", self.formatted_class_name, key, value)
                brokered_user.save()

                # the accounts that the manifest lists, e.g. an organization's departments, else the account of
                # whoever applies it.
                memberships = self.manifest.spec.accounts
                if memberships is not None:
                    self.apply_memberships(brokered_user, memberships)
                else:
                    self.apply_own_account_profile(brokered_user)
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.apply() Failed to apply manifest to Django ORM for %s: %s",
                self.formatted_class_name,
                self.kind,
                str(e),
                exc_info=True,
            )
            raise SAMUserBrokerError(
                f"Failed to apply {self.kind} {self.brokered_user.email if isinstance(self.brokered_user, User) else None}",
                thing=self.kind,
                command=command,
            ) from e
        self.cache_invalidations()
        return self.json_response_ok(command=command, data=self.command_result())

    def prompt(self, request: "HttpRequest", *args, **kwargs) -> SmarterJournaledJsonResponse:
        """
        .. attention::

            this is not implemented for the Smarter API User manifest.

        :raises: :class:`SAMBrokerErrorNotImplemented`
            Always raised to indicate that the prompt operation is not implemented for this manifest type.

        :param request: The Django `HttpRequest` object.
        :param args: Additional positional arguments.
        :param kwargs: Additional keyword arguments.

        :returns: Never returns; always raises an exception.
        """
        command = SmarterJournalCliCommands(self.prompt.__name__)
        logger.debug("%s.prompt() called", self.formatted_class_name)
        raise SAMBrokerErrorNotImplemented(message="Prompt not implemented", thing=self.kind, command=command)

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
        command = SmarterJournalCliCommands(self.describe.__name__)
        logger.debug("%s.describe() called", self.formatted_class_name)

        if self.manifest is None:
            raise SAMBrokerErrorNotFound(f"{self.kind} {self.name} not found", thing=self.kind, command=command)
        if not isinstance(self.manifest, SAMUser):
            raise SAMUserBrokerError(
                message=f"Manifest must be of type {SAMUser.__name__} to describe, got {type(self.manifest)}: {self.manifest}",
                thing=self.kind,
                command=command,
            )

        if not self.brokered_user:
            raise SAMBrokerErrorNotFound(f"Failed to describe {self.kind}. Not found", thing=self.kind, command=command)

        try:
            self._user = User.objects.get(username=self.username)
        except User.DoesNotExist as e:
            raise SAMBrokerErrorNotFound(
                f"Failed to describe {self.kind} {self.username}. Not found", thing=self.kind, command=command
            ) from e

        try:
            self._user_profile = UserProfile.get_cached_object(user=self._user, account=self.account)
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

    @classmethod
    def dependents(cls, instance: User) -> SAMDependents:
        """Return the resources that a User owns.

        Deleting a User also deletes every resource that it owns, so they must be deleted, or
        moved to another owner, first.

        :param instance: The User.
        :type instance: User
        :return: The resources of each kind that the User owns. Its plugins have their own kinds.
        :rtype: SAMDependents
        """
        # pylint: disable=import-outside-toplevel
        from smarter.apps.api.v1.manifests.enum import SAMKinds
        from smarter.apps.connection.models import ApiConnection, SqlConnection
        from smarter.apps.guardrail.models import Guardrail
        from smarter.apps.llmclient.models import LLMClient, LLMClientCustomDomain
        from smarter.apps.llmhost.models import LLMHost, LLMHostCompute
        from smarter.apps.llmtool.models import PluginMeta
        from smarter.apps.mcpclient.models import MCPClient
        from smarter.apps.orchestrator.models import Orchestrator
        from smarter.apps.provider.models import Provider
        from smarter.apps.proxy.models import Proxy
        from smarter.apps.secret.models import Secret
        from smarter.apps.vectorsearch.models import Vectorsearch
        from smarter.apps.vectorstore.models import VectorstoreMeta
        from smarter.lib.drf.models import SmarterAuthToken

        retval: SAMDependents = [
            (kind.value, model.objects.filter(user_profile__user=instance))
            for kind, model in (
                (SAMKinds.API_CONNECTION, ApiConnection),
                (SAMKinds.SQL_CONNECTION, SqlConnection),
                (SAMKinds.CUSTOM_DOMAIN, LLMClientCustomDomain),
                (SAMKinds.GUARDRAIL, Guardrail),
                (SAMKinds.LLM_CLIENT, LLMClient),
                (SAMKinds.LLM_HOST, LLMHost),
                (SAMKinds.LLM_HOST_COMPUTE, LLMHostCompute),
                (SAMKinds.MCP_CLIENT, MCPClient),
                (SAMKinds.ORCHESTRATOR, Orchestrator),
                (SAMKinds.PROVIDER, Provider),
                (SAMKinds.PROXY, Proxy),
                (SAMKinds.SECRET, Secret),
                (SAMKinds.VECTORSEARCH, Vectorsearch),
                (SAMKinds.VECTORSTORE, VectorstoreMeta),
                (SAMKinds.AUTH_TOKEN, SmarterAuthToken),
            )
        ]
        retval.append((None, PluginMeta.objects.filter(user_profile__user=instance)))
        return retval

    @classmethod
    def references(cls, instance: User) -> SAMDependents:
        """Return the resources that a User uses: none.

        :param instance: The User.
        :type instance: User
        :return: An empty list.
        :rtype: SAMDependents
        """
        return []

    @memoized_dependencies
    def dependencies(self) -> List[SAMDependency]:
        """Return brokers for the resources that this User owns.

        Deleting a User also deletes every resource that it owns, so they must be deleted, or
        moved to another owner, first.

        :return: A broker for each resource that the User owns.
        :rtype: List[SAMDependency]
        """
        return self.dependency_brokers_for(self.brokered_user)

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
        command = SmarterJournalCliCommands(self.delete.__name__)
        logger.debug("%s.delete() called", self.formatted_class_name)

        if not isinstance(self.user, User):
            raise SAMUserBrokerError(
                message=f"Authenticated user must be a User instance, got {type(self.user)}: {self.user}",
                thing=self.kind,
                command=command,
            )

        if not self.administers_account:
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

        self._brokered_user = user
        self.verify_no_dependencies(command)
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
        command = SmarterJournalCliCommands(self.deploy.__name__)
        logger.debug("%s.deploy() called", self.formatted_class_name)

        if not isinstance(self.user, User):
            raise SAMUserBrokerError(
                message=f"Authenticated user must be a User instance, got {type(self.user)}: {self.user}",
                thing=self.kind,
                command=command,
            )

        if not self.administers_account:
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
        command = SmarterJournalCliCommands(self.undeploy.__name__)
        logger.debug("%s.undeploy() called", self.formatted_class_name)

        if not isinstance(self.user, User):
            raise SAMUserBrokerError(
                message=f"Authenticated user must be a User instance, got {type(self.user)}: {self.user}",
                thing=self.kind,
                command=command,
            )

        if not self.administers_account:
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
        command = SmarterJournalCliCommands(self.logs.__name__)
        logger.debug("%s.logs() called", self.formatted_class_name)

        data: SmarterDictType = {}
        return self.json_response_ok(command=command, data=data)
