"""Account MetaDataWithOwnership model."""

import logging
from typing import Optional, TypeVar

# django stuff
from django.contrib.auth.models import User
from django.core.handlers.wsgi import WSGIRequest
from django.db import models
from django.db.models import Manager, QuerySet
from typing_extensions import deprecated

# our stuff
from smarter.common.const import SMARTER_ACCOUNT_NUMBER
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.models import MetaDataModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .account import Account, get_resolved_user, is_authenticated_user
from .user_profile import UserProfile


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


_MT = TypeVar("_MT", bound="MetaDataWithOwnershipModel")
"""
Type variable for MetaDataWithOwnershipModel. Used for type hinting in the
custom queryset and manager to ensure methods return the correct model type.

.. seealso::

    - django-stubs: Custom QuerySets <https://github.com/typeddjango/django-stubs>_
"""


class SmarterQuerySetWithPermissions(QuerySet[_MT]):
    """
    Custom queryset for permission-based resource filtering by user profile.

    This queryset adds permission-aware filtering for resources owned by a specific user profile.

    .. seealso::

        - Django: Creating a manager with QuerySet methods <https://docs.djangoproject.com/en/6.0/topics/db/managers/#creating-a-manager-with-queryset-methods>_
        - django-stubs: Custom QuerySets <https://github.com/typeddjango/django-stubs>_

    """

    def with_read_permission_for(self, user: User) -> "SmarterQuerySetWithPermissions[_MT]":
        """
        A pipeline for filtering a queryset of this resource based on the
        permissions of the authenticated user in the given request.

        Return a queryset of this resource if the user has permission to read it,
        or an empty queryset if not.

        :param user: :class:`django.contrib.auth.models.User`
            The user to check.
        :param queryset: Optional[:class:`django.db.models.QuerySet`]
            An optional queryset to filter. If not provided, the method will default to filtering all instances

        :returns: :class:`django.db.models.QuerySet`
            A queryset of this resource if the user has permission to read it, or an empty queryset
            if not.
        """
        logger.debug(
            "%s.with_read_permission_for() called for user: %s",
            formatted_text(__name__ + ".SmarterQuerySetWithPermissions"),
            user,
        )
        if not is_authenticated_user(user):
            return self.none()
        request_user_profile = UserProfile.get_cached_object(user=user)
        if not request_user_profile:
            return self.none()
        if request_user_profile.user.is_superuser:
            return self.all()
        smarter_account = Account.get_cached_object(account_number=SMARTER_ACCOUNT_NUMBER)
        return self.filter(
            models.Q(user_profile__account=smarter_account)
            | models.Q(user_profile=request_user_profile)
            | models.Q(user_profile__account=request_user_profile.account, user_profile__user__is_staff=True)
        )

    def with_ownership_permission_for(self, user: User) -> "SmarterQuerySetWithPermissions[_MT]":
        """
        Returns a queryset of resources that the authenticated user in the given request has full management (ownership) permission for.

        Only users with staff or superuser status are permitted to manage resources.

        :param user: :class:`django.contrib.auth.models.User`
            The user to check.
        :returns: :class:`django.db.models.QuerySet`
            A queryset of this resource if the user has permission to fully manage it, or an empty queryset if not.
        """
        if not isinstance(user, User):
            return self.none()
        if not is_authenticated_user(user):
            return self.none()

        # superusers have ownership permission for all resources
        if user.is_superuser:
            return self.all()
        user_profile = UserProfile.get_cached_object(user=user)
        if not user_profile:
            return self.none()

        # staff users have ownership permission for resources owned within their account, or owned by themselves
        if user.is_staff:
            return self.filter(
                models.Q(user_profile=user_profile) | models.Q(user_profile__account=user_profile.account)
            )

        # regular authenticated users have ownership permission only for resources they own
        return self.filter(user_profile=user_profile)


class MetaDataWithOwnershipModelManager(Manager[_MT]):
    """
    Custom manager for MetaDataWithOwnershipModel that returns a
    SmarterQuerySetWithPermissions to enable permission-based filtering by
    user_profile.
    """

    def get_queryset(self) -> SmarterQuerySetWithPermissions[_MT]:
        return SmarterQuerySetWithPermissions(self.model, using=self._db)

    def filter(self, *args, **kwargs) -> SmarterQuerySetWithPermissions[_MT]:
        return self.get_queryset().filter(*args, **kwargs)

    def with_read_permission_for(self, user: User) -> SmarterQuerySetWithPermissions[_MT]:
        """
        A custom Smarter pipeline for filtering any MetaDataWithOwnership
        queryset based on the Smarter permissions scheme for the authenticated user in
        the given request.

        Returns a queryset of the resource if the user has permission to read it,
        or an empty queryset if not.

        Permission logic:

        - If the user is not authenticated, they have no access.
        - If the user is a superuser, they have access to all resources.
        - If the user is a regular authenticated user, they have access to resources that are:
            - Owned by their UserProfile, OR
            - Owned by their Account admin UserProfile, OR
            - Owned by the Smarter admin UserProfile.

        :param user: :class:`django.contrib.auth.models.User`
            The user to check.
        :param queryset: Optional[:class:`django.db.models.QuerySet`]
            An optional queryset to filter. If not provided, the method will default to filtering all instances

        :returns: :class:`django.db.models.QuerySet`
            A queryset of this resource if the user has permission to read it, or an empty queryset
            if not.
        """
        return self.get_queryset().with_read_permission_for(user)

    def with_ownership_permission_for(self, user: User) -> SmarterQuerySetWithPermissions[_MT]:
        """
        Returns a queryset of resources that the authenticated user in the given request has full management (ownership) permission for.

        Permission logic:

        - If the user is not authenticated, they have no access.
        - If the user is a superuser, they have ownership permission for all resources.
        - If the user is a staff user, they have ownership permission for resources that are:
            - Owned by their UserProfile, OR
            - Owned by any UserProfile within their Account.
        - If the user is a regular authenticated user, they have ownership permission only for resources they own.

        :param user: :class:`django.contrib.auth.models.User`
            The user to check.
        :returns: :class:`django.db.models.QuerySet`
            A queryset of this resource if the user has permission to fully manage it, or an empty queryset if not.
        """
        return self.get_queryset().with_ownership_permission_for(user)


class MetaDataWithOwnershipModel(MetaDataModel):
    """
    Abstract Django ORM base model that adds Account and
    User ownership to a SAM Metadata model.

    This model extends `MetaDataModel` to include a foreign key
    relationship to the `UserProfile` model, establishing ownership of resources
    by a specific user profile. It also enforces uniqueness constraints on
    the combination of `user_profile` and `name` fields,

    :param user_profile: ForeignKey to :class:`UserProfile`. The user profile that owns this resource.

    .. note::

        This is an abstract base class and should not be instantiated directly.
    """

    # pylint: disable=missing-class-docstring
    class Meta:
        abstract = True
        unique_together = (
            "user_profile",
            "name",
        )

    objects: MetaDataWithOwnershipModelManager = MetaDataWithOwnershipModelManager()

    user_profile = models.ForeignKey(UserProfile, on_delete=models.CASCADE, related_name="%(class)ss")

    @deprecated(
        "Use model.objects.with_ownership_permission_for(user=user) on the queryset instead for more efficient permission checks."
    )
    def has_all_permission(self, request: WSGIRequest) -> bool:
        """
        Check if the authenticated user in the given request has permission to
        fully manage this resource.

        :param request: :class:`django.core.handlers.wsgi.WSGIRequest`
            The HTTP request containing the user to check.

        :returns: bool

            True if the user is authenticated and is either staff or superuser; False otherwise.

        .. attention::

            Only users with staff or superuser status are permitted to manage resources.

        .. warning::

            If the request does not contain a valid user, or the user lacks required privileges, permission is denied.

        **Example usage**::

            if resource.has_all_permission(request):
                # Allow resource management
                pass

        .. seealso::

            :meth:`get_resolved_user` -- Resolves the user from the request.
        """
        if not hasattr(request, "user"):
            return False
        user = get_resolved_user(request.user)
        if not isinstance(user, User):
            return False
        if not hasattr(user, "is_authenticated") or not user.is_authenticated:
            return False
        if not hasattr(user, "is_staff") or not hasattr(user, "is_superuser"):
            return False
        return user.is_staff or user.is_superuser

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        name: Optional[str] = None,
        user: Optional[User] = None,
        user_profile: Optional[UserProfile] = None,
        username: Optional[str] = None,
        account: Optional[Account] = None,
        **kwargs,
    ) -> models.Model:
        """
        Retrieve a model instance using caching to optimize performance.

        Examples of retrieval patterns:

        .. code-block:: python

            # By primary key
            instance = MyModel.get_cached_object(pk=123)

            # By name and user profile
            instance = MyModel.get_cached_object(name="Resource Name", user_profile=user_profile)

            # By name and account
            instance = MyModel.get_cached_object(name="Resource Name", account=account)

        :param pk: The primary key of the model instance to retrieve.
        :param name: The name of the model instance to retrieve.
        :param user: The user associated with the model instance.
        :param user_profile: The user profile associated with the model instance.
        :param account: The account associated with the model instance.
        :param invalidate: Whether to invalidate the cache for this retrieval.

        :returns: The model instance if found, otherwise raises :class:`DoesNotExist`.
        :rtype: models.Model
        """
        logger_prefix = formatted_text(cls.__name__ + ".get_cached_object()")
        logger.debug(
            "%s called with pk: %s, name: %s, user: %s, user_profile: %s, username: %s, account: %s",
            logger_prefix,
            pk,
            name,
            user,
            user_profile,
            username,
            account,
        )

        if username and not user and not user_profile:
            logger.debug("%s Resolving user_profile from username: %s", logger_prefix, username)
            user_profile = UserProfile.get_cached_object(invalidate=invalidate, username=username)
            user = user_profile.cached_user if user_profile else None

        if user_profile is not None and (not user or not account):
            logger.debug("%s Resolving user and account from user_profile: %s", logger_prefix, user_profile)
            user = user or user_profile.cached_user
            account = account or user_profile.cached_account

        @cache_results(cls.cache_expiration)
        def _get_object_by_pk(pk: int, class_name: str = cls.__name__) -> Optional["MetaDataWithOwnershipModel"]:
            """
            Internal method to retrieve a model instance by primary key with caching.
            Prefetches related tags and selects related user profile, account, and
            user for optimal access. Handles most common SAM pk retrieval scenarios.

            :param pk: The primary key of the model instance to retrieve.
            :param class_name: The name of the class for logging purposes.
            :class_name: The name of the class for cache key purposes.
            :returns: The model instance if found, otherwise None.
            :rtype: Optional["MetaDataWithOwnershipModel"]
            """
            try:
                retval = (
                    cls.objects.prefetch_related("tags")
                    .select_related("user_profile", "user_profile__account", "user_profile__user")
                    .get(pk=pk)
                )
                logger.debug(
                    "%s._get_object_by_pk() fetched %s - %s",
                    formatted_text(MetaDataWithOwnershipModel.__name__ + ".get_cached_object()"),
                    type(retval).__name__,
                    str(retval),
                )
                return retval
            except cls.DoesNotExist:
                logger.debug(
                    "%s._get_object_by_pk() no %s object found for pk: %s",
                    formatted_text(MetaDataWithOwnershipModel.__name__ + ".get_cached_object()"),
                    cls.__name__,
                    pk,
                )
                return None

        @cache_results(cls.cache_expiration)
        def _get_object_by_name_and_user_profile(
            name: str, user_profile: UserProfile, class_name: str = cls.__name__
        ) -> Optional["MetaDataWithOwnershipModel"]:
            """
            Internal method to retrieve a model instance by name and user
            profile with caching. Prefetches related tags and selects
            related user profile, account, and user for optimal access.
            Handles common SAM retrieval patterns for name/user.

            :param name: The name of the model instance to retrieve.
            :param user_profile: The user profile associated with the model instance.
            :param class_name: The name of the class for cache key purposes.

            :returns: The model instance if found, otherwise None.
            :rtype: Optional["MetaDataWithOwnershipModel"]
            """
            try:
                retval = (
                    cls.objects.prefetch_related("tags")
                    .select_related("user_profile", "user_profile__account", "user_profile__user")
                    .get(name=name, user_profile=user_profile)
                )
                logger.debug(
                    "%s._get_object_by_name_and_user_profile() fetched %s for name: %s and user_profile: %s",
                    formatted_text(MetaDataWithOwnershipModel.__name__ + ".get_cached_object()"),
                    type(retval).__class__.__name__,
                    name,
                    user_profile,
                )
                return retval
            except cls.DoesNotExist:
                logger.debug(
                    "%s._get_object_by_name_and_user_profile() no %s found for name: %s and user_profile: %s",
                    formatted_text(MetaDataWithOwnershipModel.__name__ + ".get_cached_object()"),
                    cls.__name__,
                    name,
                    user_profile,
                )
                return None
            except cls.MultipleObjectsReturned:
                logger.error(
                    "%s.get_cached_object() Multiple %s objects found with name '%s' and user profile '%s'. Defaulting to first result.",
                    formatted_text(MetaDataWithOwnershipModel.__name__ + ".get_cached_object()"),
                    cls.__name__,
                    name,
                    user_profile,
                )
                return cls.objects.prefetch_related("tags").filter(name=name, user_profile=user_profile).first()

        @cache_results(cls.cache_expiration)
        def _get_object_by_name_and_account(
            name: str, account: Account, class_name: str = cls.__name__
        ) -> Optional["MetaDataWithOwnershipModel"]:
            """
            Internal method to retrieve a model instance by name and account with
            caching. Prefetches related tags and selects related user profile,
            account, and user for optimal access. Handles common SAM retrieval
            patterns for name/account.

            :param name: The name of the model instance to retrieve.
            :param account: The account associated with the model instance.
            :param class_name: The name of the class for cache key purposes.

            :returns: The model instance if found, otherwise None.
            :rtype: Optional["MetaDataWithOwnershipModel"]
            """
            try:
                retval = (
                    cls.objects.prefetch_related("tags")
                    .select_related("user_profile", "user_profile__account", "user_profile__user")
                    .get(name=name, user_profile__account=account)
                )
                logger.debug(
                    "%s._get_object_by_name_and_account() fetched %s for name: %s and account: %s",
                    formatted_text(MetaDataWithOwnershipModel.__name__ + ".get_cached_object()"),
                    type(retval).__class__.__name__,
                    name,
                    account,
                )
                return retval
            except cls.DoesNotExist:
                logger.debug(
                    "%s._get_object_by_name_and_account() no %s found for name: %s and account: %s",
                    formatted_text(MetaDataWithOwnershipModel.__name__ + ".get_cached_object()"),
                    cls.__name__,
                    name,
                    account,
                )
                return None
            except cls.MultipleObjectsReturned:
                logger.error(
                    "%s.get_cached_object() Multiple %s objects found with name '%s' and account '%s'. Defaulting to first result.",
                    formatted_text(MetaDataWithOwnershipModel.__name__ + ".get_cached_object()"),
                    cls.__name__,
                    name,
                    account,
                )
                return cls.objects.prefetch_related("tags").filter(name=name, user_profile__account=account).first()

        if invalidate:
            _get_object_by_pk.invalidate(pk=pk, class_name=cls.__name__)
            _get_object_by_name_and_user_profile.invalidate(
                name=name, user_profile=user_profile, class_name=cls.__name__
            )
            _get_object_by_name_and_account.invalidate(name=name, account=account, class_name=cls.__name__)

        if pk:
            return _get_object_by_pk(pk=pk, class_name=cls.__name__)

        try:
            user_profile = user_profile or UserProfile.get_cached_object(user=user, account=account)
        except UserProfile.DoesNotExist:
            user_profile = None
        except UserProfile.MultipleObjectsReturned:
            logger.error(
                "%s.get_cached_object() Multiple UserProfiles found for user %s and account %s. Defaulting to first result.",
                formatted_text(cls.__name__ + ".get_cached_object()"),
                user,
                account,
            )
            user_profile = (
                UserProfile.objects.select_related("user_profile", "user_profile__account", "user_profile__user")
                .prefetch_related("tags")
                .filter(user=user, account=account)
                .first()
            )

        if user_profile:
            # call this regardless of whether name is provided.
            return _get_object_by_name_and_user_profile(name=name, user_profile=user_profile, class_name=cls.__name__)
        elif account:
            return _get_object_by_name_and_account(name=name, account=account, class_name=cls.__name__)

        # no ownership info provided, so fall back to the super().
        return super().get_cached_object(*args, invalidate=invalidate, pk=pk, name=name, **kwargs)  # type: ignore[return-value]

    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, user_profile: Optional[UserProfile] = None
    ) -> models.QuerySet["MetaDataWithOwnershipModel"]:
        """
        Retrieve a list of MetaDataWithOwnershipModel instances associated with a user profile using caching.

        Example usage:

        .. code-block:: python

            # Retrieve MetaDataWithOwnershipModel instances for a user profile with caching
            models = MetaDataWithOwnershipModel.get_cached_objects(my_user_profile, invalidate=invalidate)

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param user_profile: The user profile for which to retrieve MetaDataWithOwnershipModel instances.
        :type user_profile: UserProfile, optional

        :returns: A queryset of MetaDataWithOwnershipModel instances associated with the user profile.
        :rtype: models.QuerySet["MetaDataWithOwnershipModel"]

        """
        logger_prefix = formatted_text(__name__ + f".{MetaDataWithOwnershipModel.__name__}.get_cached_objects()")
        logger.debug(
            "%s called for %s with user_profile: %s invalidate: %s",
            logger_prefix,
            cls.__name__,
            user_profile,
            invalidate,
        )

        @cache_results(cls.cache_expiration)
        def _get_objects_for_user_profile_id(
            user_profile_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["MetaDataWithOwnershipModel"]:
            """
            Internal method to retrieve MetaDataWithOwnershipModel instances for
            a given user profile ID with caching.

            :param user_profile_id: The ID of the user profile for which to retrieve MetaDataWithOwnershipModel instances.
            :param class_name: The name of the class for cache key purposes.
            :returns: A queryset of MetaDataWithOwnershipModel instances associated with the user profile ID.
            :rtype: models.QuerySet["MetaDataWithOwnershipModel"]
            """
            return (
                cls.objects.prefetch_related("tags")
                .select_related("user_profile", "user_profile__account", "user_profile__user")
                .filter(user_profile_id=user_profile_id)
            )

        if invalidate and user_profile:
            _get_objects_for_user_profile_id.invalidate(user_profile_id=user_profile.id, class_name=cls.__name__)  # type: ignore

        if user_profile:
            return _get_objects_for_user_profile_id(user_profile_id=user_profile.id, class_name=cls.__name__)  # type: ignore

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]


__all__ = ["MetaDataWithOwnershipModel", "MetaDataWithOwnershipModelManager", "SmarterQuerySetWithPermissions"]
