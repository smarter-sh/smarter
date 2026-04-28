"""Account UserProfile model."""

import logging
import os
from typing import Any, Optional, TypeVar, overload

# django stuff
from django.contrib.auth.models import User
from django.db import models
from django.db.models import Manager, QuerySet
from django.db.models.expressions import Combinable
from django.db.models.query import Prefetch

# our stuff
from smarter.apps.account.signals import new_user_created
from smarter.common.const import SMARTER_ADMIN_USERNAME
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.console_helpers import formatted_text
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.models import MetaDataModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .account import Account, AccountContact

HERE = os.path.abspath(os.path.dirname(__file__))

_GenericTypeVar = TypeVar("_GenericTypeVar", bound="models.Model")
"""
Generic Manager Type variable bound to any Django Model, so that it
its associated Manager can be type hinted to return the correct model type.
Used for type hinting in the custom queryset and manager to ensure methods
return the correct model type.

.. seealso::

    - django-stubs: Custom QuerySets <https://github.com/typeddjango/django-stubs>_
"""


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class SmarterBaseQuerySetWithPermissions(QuerySet[_GenericTypeVar]):
    """
    Custom queryset for permission-based resource filtering by user profile.

    This queryset adds permission-aware filtering for resources owned by a specific user profile.

    .. seealso::

        - Django: Creating a manager with QuerySet methods <https://docs.djangoproject.com/en/6.0/topics/db/managers/#creating-a-manager-with-queryset-methods>_
        - django-stubs: Custom QuerySets <https://github.com/typeddjango/django-stubs>_

    """

    def with_read_permission_for(self, user: User) -> "SmarterBaseQuerySetWithPermissions[_GenericTypeVar]":
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
            formatted_text(__name__ + ".SmarterBaseQuerySetWithPermissions"),
            user,
        )
        if user.is_superuser:
            logger.debug(
                "%s.with_read_permission_for() user is superuser, returning all resources. count: %s",
                formatted_text(__name__ + ".SmarterBaseQuerySetWithPermissions"),
                self.count(),
            )
            return self.all()
        return self.none()

    def with_ownership_permission_for(self, user: User) -> "SmarterBaseQuerySetWithPermissions[_GenericTypeVar]":
        """
        Returns a queryset of resources that the authenticated user in the given request has full management (ownership) permission for.

        Only users with staff or superuser status are permitted to manage resources.

        :param user: :class:`django.contrib.auth.models.User`
            The user to check.
        :returns: :class:`django.db.models.QuerySet`
            A queryset of this resource if the user has permission to fully manage it, or an empty queryset if not.
        """
        logger.debug(
            "%s.with_ownership_permission_for() called for user: %s",
            formatted_text(__name__ + ".SmarterBaseQuerySetWithPermissions"),
            user,
        )
        if not isinstance(user, User):
            logger.debug(
                "%s.with_ownership_permission_for() user is not an instance of User: %s",
                formatted_text(__name__ + ".SmarterBaseQuerySetWithPermissions"),
                user,
            )
            return self.none()

        if user.is_superuser:
            logger.debug(
                "%s.with_ownership_permission_for() user is superuser, returning all resources. count: %s",
                formatted_text(__name__ + ".SmarterBaseQuerySetWithPermissions"),
                self.count(),
            )
            return self.all()
        return self.none()


class SmarterBaseModelManager(Manager[_GenericTypeVar]):
    """
    Custom manager for MetaDataWithOwnershipModel that returns a
    SmarterBaseQuerySetWithPermissions to enable permission-based filtering by
    user_profile.
    """

    # --------------------------------------------------------------------------
    # Override base Manager methods to return SmarterBaseQuerySetWithPermissions
    # to ensure all queries go through the permission-aware queryset.
    # --------------------------------------------------------------------------
    def get_queryset(self) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """
        Returns a SmarterBaseQuerySetWithPermissions for the model.
        """
        return SmarterBaseQuerySetWithPermissions(self.model, using=self._db)

    def filter(self, *args, **kwargs) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """
        Returns a SmarterBaseQuerySetWithPermissions with the applied filter.
        """
        return self.get_queryset().filter(*args, **kwargs)

    def exclude(self, *args, **kwargs) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """
        Returns a SmarterBaseQuerySetWithPermissions with the applied exclusion.
        """
        return self.get_queryset().exclude(*args, **kwargs)

    def none(self) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns an empty SmarterBaseQuerySetWithPermissions."""
        return self.get_queryset().none()

    def complex_filter(self, filter_obj) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions with the applied complex filter."""
        return self.get_queryset().complex_filter(filter_obj)

    def union(self, *other_qs, all=False) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions representing the union of querysets."""
        return self.get_queryset().union(*other_qs, all=all)

    def intersection(self, *other_qs) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions representing the intersection of querysets."""
        return self.get_queryset().intersection(*other_qs)

    def difference(self, *other_qs) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions representing the difference of querysets."""
        return self.get_queryset().difference(*other_qs)

    def select_for_update(self, **kwargs) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions with select_for_update applied."""
        return self.get_queryset().select_for_update(**kwargs)

    @overload
    def select_related(self, clear: None, /) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]: ...
    @overload
    def select_related(self, *fields: str) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]: ...
    def select_related(self, *args, **kwargs) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions with select_related applied."""
        return self.get_queryset().select_related(*args, **kwargs)

    @overload
    def prefetch_related(self, clear: None, /) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]: ...
    @overload
    def prefetch_related(self, *lookups: str | Prefetch) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]: ...
    def prefetch_related(self, *args, **kwargs) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """
        Returns a SmarterBaseQuerySetWithPermissions with prefetch_related applied.
        """
        return self.get_queryset().prefetch_related(*args, **kwargs)

    def annotate(self, *args: Any, **kwargs: Any) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions with annotate applied."""
        return self.get_queryset().annotate(*args, **kwargs)

    def alias(self, *args: Any, **kwargs: Any) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions with alias applied."""
        return self.get_queryset().alias(*args, **kwargs)

    def order_by(self, *field_names: str | Combinable) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions with order_by applied."""
        return self.get_queryset().order_by(*field_names)

    def distinct(self, *field_names: str) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
        """Returns a SmarterBaseQuerySetWithPermissions with distinct applied."""
        return self.get_queryset().distinct(*field_names)

    # --------------------------------------------------------------------------
    # Custom permission-based queryset methods for filtering by user_profile
    # read and ownership permissions.
    # --------------------------------------------------------------------------
    def with_read_permission_for(self, user: User) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
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
        logger.debug(
            "%s.with_read_permission_for() called for user: %s",
            formatted_text(__name__ + ".SmarterBaseModelManager"),
            user,
        )
        return self.get_queryset().with_read_permission_for(user)

    def with_ownership_permission_for(self, user: User) -> SmarterBaseQuerySetWithPermissions[_GenericTypeVar]:
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
        logger.debug(
            "%s.with_ownership_permission_for() called for user: %s",
            formatted_text(__name__ + ".SmarterBaseModelManager"),
            user,
        )
        return self.get_queryset().with_ownership_permission_for(user)


class UserProfile(MetaDataModel):
    """
    UserProfile model for associating Django users with Smarter accounts.

    Establishes a link between a Django User and an Account, enabling centralized management of billing, identity, and resource ownership.

    :param user: ForeignKey to :class:`django.contrib.auth.models.User`. The user associated with this profile.
    :param account: ForeignKey to :class:`Account`. The related Smarter account.
    :param is_test: Boolean. Indicates if this profile is for testing purposes.

    .. important::

        The combination of `user` and `account` must be unique. Duplicate profiles for the same user and account are not allowed.

    **Example usage**::

        from smarter.apps.account.models import UserProfile
        profile = UserProfile.objects.create(user=user, account=account)
        profile.add_to_account_contacts(is_primary=True)

    """

    # pylint: disable=missing-class-docstring
    class Meta:
        unique_together = (
            "user",
            "account",
        )

    objects: SmarterBaseModelManager = SmarterBaseModelManager()

    # Add more fields here as needed
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="user_profile",
    )
    account = models.ForeignKey(Account, on_delete=models.CASCADE, related_name="user_profiles")
    profile_image_url = models.URLField(
        blank=True, null=True, help_text="URL to the user's profile image, provided via oauth."
    )
    is_test = models.BooleanField(
        default=False, help_text="Indicates if this profile is used for unit testing purposes."
    )

    @property
    def cached_user(self) -> Optional[User]:
        """
        Retrieve the associated User instance with caching.
        This significantly reduces the number of database queries when accessing
        the user from the user profile.

        :returns: Optional[User]
            The associated User instance, or None if not found.

        **Example usage**::

            user = profile.cached_user
            if user:
                print(user.email)

        """
        return self.user

    @property
    def cached_account(self) -> Optional[Account]:
        """
        Retrieve the associated Account instance with caching.
        This significantly reduces the number of database queries
        when accessing the account from the user profile.

        :returns: Optional[Account]
            The associated Account instance, or None if not found.

        **Example usage**::

            account = user_profile.cached_account
            if account:
                print(account.company_name)

        """
        return self.account

    def add_to_account_contacts(self, is_primary: bool = False):
        """
        Add the user to the account's contact list.

        Creates or updates an `AccountContact` entry for the user, ensuring their email and name are registered with the account.
        Optionally sets the contact as primary.

        :param is_primary: Boolean. If True, marks the contact as the primary contact for the account. Defaults to False.

        .. important::

            Ensures every user associated with an account is also listed as a contact, supporting notifications and account management.

        **Example usage**::

            profile.add_to_account_contacts(is_primary=True)

        .. seealso::

            :class:`AccountContact`
        """
        account_contact, _ = AccountContact.objects.get_or_create(
            account=self.account,
            email=self.user.email,
            is_test=self.is_test,
            first_name=self.user.first_name or "account",
            last_name=self.user.last_name or "contact",
        )
        if account_contact.is_primary != is_primary:
            account_contact.is_primary = is_primary
            account_contact.save()

    def save(self, *args, **kwargs):
        """
        Save the UserProfile instance and ensure account contacts are updated.

        This method validates that both `user` and `account` are set, saves the profile, and, if newly created,
        adds the user to the account's contact list. It also emits a signal for new user creation.

        :param args: Positional arguments passed to the parent save method.
        :param kwargs: Keyword arguments passed to the parent save method.

        .. note::

            On first save, ensures at least one primary contact exists for the account.

        **Example usage**::

            profile.save()

        """
        is_new = self.pk is None

        if self.user is None or self.account is None:
            raise SmarterValueError("User and Account cannot be null")
        super().save(*args, **kwargs)
        if is_new:
            # ensure that at least one person is on the account contact list
            is_primary = AccountContact.objects.filter(account=self.account, is_primary=True).count() == 0
            self.add_to_account_contacts(is_primary=is_primary)

            logger.debug(
                "%s.save() New user profile created for %s %s. Sending signal.",
                formatted_text(__name__ + ".UserProfile()"),
                self.account.company_name,
                self.user.email,
            )
            new_user_created.send(sender=self.__class__, user_profile=self)
        else:
            # if account or user is updated, raise an error since that should not happen.
            orig = UserProfile.objects.get(pk=self.pk)
            if orig.account != self.account or orig.user != self.user:
                raise SmarterValueError("Cannot change the account or user of an existing UserProfile")

    @classmethod
    def admin_for_account(cls, account: Account) -> User:
        """
        Return the designated user for the given account.

        This method finds the first staff user associated with the account. If no staff user exists, it returns the first available user.
        If the account has no users, an admin user is created and returned.

        :param account: Instance of :class:`Account`. The account for which to find the designated user.
        :returns: :class:`django.contrib.auth.models.User`
            The designated user for the account.

        .. attention::

            If no staff or regular users exist for the account, an admin user is automatically created. You must set the password manually.

        .. error::

            Logs an error if no admin or user is found for the account.

        **Example usage**::

            user = UserProfile.admin_for_account(account)

        .. seealso::

            :class:`UserProfile`
        """

        @cache_results(cls.cache_expiration)
        def _get_admin_for_account(account_id: int, class_name: str) -> Optional[User]:

            admins = cls.objects.filter(account_id=account_id, user__is_staff=True).order_by("user__id")
            if admins.exists():
                return admins.first().user  # type: ignore[return-value]

            logger.error(
                "%s.admin_for_account() No admin found for account %s",
                formatted_text(__name__ + ".UserProfile()"),
                account,
            )

            users = cls.objects.filter(account_id=account_id).order_by("user__id")
            if users.exists():
                user = users.first().user  # type: ignore[return-value]
                return user

            logger.error(
                "%s.admin_for_account() No user for account %s", formatted_text(__name__ + ".UserProfile()"), account
            )
            admin_user, _ = User.objects.get_or_create(username=SMARTER_ADMIN_USERNAME)
            user_profile = cls.objects.create(user=admin_user, account=account)
            logger.warning(
                "%s.admin_for_account() Created admin user for account %s. Use manage.py to set the password",
                formatted_text(__name__ + ".UserProfile()"),
                account,
            )
            return user_profile.user

        return _get_admin_for_account(account_id=account.id, class_name=UserProfile.__name__)  # type: ignore[return-value]

    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        name: Optional[str] = None,
        user: Optional[User] = None,
        username: Optional[str] = None,
        account: Optional[Account] = None,
        **kwargs,
    ) -> "UserProfile":
        """
        Retrieve a model instance by primary key or name, using caching to
        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)
            # Retrieve by name
            instance = MyModel.get_cached_object(name="exampleName")

        :param pk: The primary key of the model instance to retrieve.
        :param name: The name of the model instance to retrieve.
        :returns: The model instance if found, otherwise None.
        :rtype: Optional["UserProfile"]
        """
        logger_prefix = formatted_text(__name__ + ".UserProfile.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, name: %s, user: %s, username: %s, account: %s, invalidate: %s",
            logger_prefix,
            pk,
            name,
            user,
            username,
            account,
            invalidate,
        )

        @cache_results(cls.cache_expiration)
        def _get_object_by_user_and_account(
            user: User, account: Account, class_name: str = cls.__name__
        ) -> "UserProfile":
            try:
                retval = (
                    UserProfile.objects.prefetch_related("tags")
                    .select_related("user", "account")
                    .get(user=user, account=account)
                )
                logger.debug(
                    "%s._get_object_by_user_and_account() fetched %s for user: %s and account: %s",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    cls.__name__,
                    user.email,
                    account,
                )
                _ = retval.user
                _ = retval.account
                return retval
            except UserProfile.DoesNotExist as e:
                logger.debug(
                    "%s._get_object_by_user_and_account() no %s found for user: %s, account: %s",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    UserProfile.__name__,
                    user.email,
                    account,
                )
                raise UserProfile.DoesNotExist(f"No UserProfile found for user {user} and account {account}") from e

        @cache_results(cls.cache_expiration)
        def _get_object_by_user(user: User, class_name: str = cls.__name__) -> "UserProfile":
            try:
                retval = UserProfile.objects.prefetch_related("tags").select_related("user", "account").get(user=user)
                logger.debug(
                    "%s._get_object_by_user() fetched %s for user: %s",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    cls.__name__,
                    user.email,
                )
                _ = retval.user
                _ = retval.account
                return retval
            except UserProfile.DoesNotExist as e:
                logger.debug(
                    "%s._get_object_by_user() no %s found for user: %s",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    UserProfile.__name__,
                    user.email,
                )
                raise UserProfile.DoesNotExist(f"No UserProfile found for user {user} and account {account}") from e
            except UserProfile.MultipleObjectsReturned as e:
                logger.error(
                    "%s.get_cached_object() Multiple UserProfiles found for user %s. Defaulting to first result.",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    user.email,
                )
                retval = (
                    UserProfile.objects.prefetch_related("tags")
                    .select_related("user", "account")
                    .filter(user=user)
                    .first()
                )
                if not retval:
                    raise UserProfile.DoesNotExist(
                        f"No UserProfile found for user {user} and account {account} after MultipleObjectsReturned exception."
                    ) from e
                return retval

        @cache_results(cls.cache_expiration)
        def _get_object_by_account(account: Account, class_name: str = cls.__name__) -> Optional["UserProfile"]:
            try:
                user = UserProfile.admin_for_account(account)
                retval = (
                    UserProfile.objects.prefetch_related("tags")
                    .select_related("user", "account")
                    .get(account=account, user=user)
                )
                logger.debug(
                    "%s._get_object_by_account() fetched %s for account admin %s",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    UserProfile.__name__,
                    retval,
                )
                _ = retval.user
                _ = retval.account
                return retval
            except UserProfile.DoesNotExist:
                logger.debug(
                    "%s._get_object_by_account() no %s found for account admin %s",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    UserProfile.__name__,
                    user,
                )
                return None
            except UserProfile.MultipleObjectsReturned:
                logger.error(
                    "%s.get_cached_object() Multiple UserProfiles found for account %s. Defaulting to first result.",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    account,
                )
                return (
                    UserProfile.objects.prefetch_related("tags")
                    .select_related("user", "account")
                    .filter(account=account)
                    .first()
                )

        if username and not user:
            try:
                user = User.objects.get(username=username)
                logger.debug(
                    "%s.get_cached_object() fetched user by username: %s",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    username,
                )
            except User.DoesNotExist as e:
                logger.error(
                    "%s.get_cached_object() No user found with username %s.",
                    formatted_text(__name__ + ".UserProfile.get_cached_object()"),
                    username,
                )
                raise User.DoesNotExist(f"No user found with username {username}") from e

        if invalidate:
            _get_object_by_user_and_account.invalidate(user=user, account=account, class_name=UserProfile.__name__)
            _get_object_by_user.invalidate(user=user, class_name=UserProfile.__name__)
            _get_object_by_account.invalidate(account=account, class_name=UserProfile.__name__)

        if user or account:
            if user and account:
                return _get_object_by_user_and_account(user, account, UserProfile.__name__)
            if user:
                return _get_object_by_user(user=user, class_name=UserProfile.__name__)
            if account:
                return _get_object_by_account(account=account, class_name=UserProfile.__name__)

        return super().get_cached_object(*args, invalidate=invalidate, pk=pk, name=name, **kwargs)  # type: ignore[return-value]

    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, user: Optional[User] = None, **kwargs
    ) -> QuerySet["UserProfile"]:
        """
        Retrieve a queryset of UserProfile instances associated with the given
        user, using caching to optimize performance.

        :param invalidate: Boolean. If True, invalidates the cache for the user's profiles before retrieving.
        :param user: Optional[User]. If provided, retrieves profiles associated with this user. If not provided, retrieves all profiles.
        :returns: QuerySet[UserProfile]. A queryset of UserProfile instances associated with the
            given user, or all profiles if no user is specified.
        :rtype: QuerySet[UserProfile]
        """
        logger_prefix = formatted_text(__name__ + f".{UserProfile.__name__}.get_cached_objects()")
        logger.debug(
            "%s called with invalidate: %s,  user: %s, kwargs: %s",
            logger_prefix,
            invalidate,
            user,
            kwargs,
        )

        @cache_results(cls.cache_expiration)
        def _get_objects_by_user(user_id: int, class_name: str = cls.__name__) -> QuerySet["UserProfile"]:
            retval = UserProfile.objects.prefetch_related("tags").select_related("user", "account").filter(user=user)
            logger.debug(
                "%s._get_objects_by_user() fetched %s objects for user_id: %s. count: %s",
                formatted_text(__name__ + ".UserProfile.get_cached_objects()"),
                cls.__name__,
                user_id,
                retval.count(),
            )
            return retval

        if isinstance(user, User):
            if invalidate:
                _get_objects_by_user.invalidate(user_id=user.id, class_name=UserProfile.__name__)  # type: ignore[call-arg]
            return _get_objects_by_user(user_id=user.id, class_name=UserProfile.__name__)  # type: ignore[return-value]

        return super().get_cached_objects()  # type: ignore[return-value]

    def __str__(self):
        try:
            user_identifier = (
                self.user.email if self.user and self.user.email else (self.user.username if self.user else "NoUser")
            )
            company_name = self.account.company_name if self.account else "NoAccount"
        except User.DoesNotExist:
            user_identifier = "NoUser"
        except Account.DoesNotExist:
            company_name = "NoAccount"
        return f"{company_name}-{user_identifier}"

    def __repr__(self):
        return self.__str__()


__all__ = ["UserProfile", "SmarterBaseModelManager", "SmarterBaseQuerySetWithPermissions"]
