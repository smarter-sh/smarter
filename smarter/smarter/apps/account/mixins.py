# pylint: disable=W0613
"""A helper class that provides setters/getters for account and user."""

import logging
from typing import Optional, Union

from django.contrib.auth.models import AnonymousUser
from django.core.handlers.wsgi import WSGIRequest
from django.http import HttpRequest
from rest_framework.request import Request

from smarter.apps.account.models import User
from smarter.apps.account.serializers import UserMiniSerializer
from smarter.apps.account.utils import get_cached_user_profile
from smarter.common.classes import SmarterHelperMixin
from smarter.common.conf import settings as smarter_settings
from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.common.utils import mask_string
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.token_authentication import SmarterTokenAuthentication
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import Account, UserProfile
from .serializers import AccountMiniSerializer, UserProfileSerializer
from .utils import (
    account_number_from_url,
    get_cached_account,
    get_cached_account_for_user,
    get_cached_user_profile,
)


UserType = Union[AnonymousUser, User, None]
AccountNumberType = Optional[str]
AccountType = Optional[Account]
UserProfileType = Optional[UserProfile]
ApiTokenType = Optional[bytes]
OptionalRequestType = Optional[Union[WSGIRequest, HttpRequest, Request]]
RequestType = Union[WSGIRequest, HttpRequest, Request]


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING) and level >= smarter_settings.log_level


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class AccountMixin(SmarterHelperMixin):
    """
    AccountMixin

    Provides consistent initializations and short-lived caching of
    the account, user, and user_profile properties using various sources
    such as direct arguments, request objects, or API tokens.

    It prioritizes initialization in the following order:
    1. Explicit account_number, account, or user arguments.
    2. Request object (from kwargs or positional args), extracting user and account info.
    3. API token authentication if provided.

    Args:
        *args: Positional arguments, may include a request object.
        account_number (Optional[str]): Unique account identifier.
        account (Optional[Account]): Account instance.
        user (Union[AnonymousUser, User, None]): Django user instance.
        api_token (Optional[bytes]): API token for authentication.
        **kwargs: Additional keyword arguments, may include 'request'.

    The constructor attempts to resolve and cache the account and user information,
    logging relevant events and warnings if data cannot be resolved.
    """

    __slots__ = ("_account", "_user", "_user_profile")

    def __init__(
        self,
        *args,
        account_number: AccountNumberType = None,
        account: AccountType = None,
        user: UserType = None,
        api_token: ApiTokenType = None,
        **kwargs,
    ):
        super().__init__(*args, **kwargs)
        self._account: AccountType = None
        self._user: UserType = None
        self._user_profile: UserProfileType = None

        request: OptionalRequestType = kwargs.get("request")
        if not request and args:
            for arg in args:
                if isinstance(arg, RequestType):
                    logger.debug(
                        "%s.__init__(): received a request object: %s",
                        self.formatted_class_name,
                        self.smarter_build_absolute_uri(arg),
                    )
                    request = arg
                    break

        if isinstance(account_number, str):
            logger.info("%s.__init__(): received account_number %s", self.formatted_class_name, account_number)
            self._account = get_cached_account(account_number=account_number) if account_number else account
        if isinstance(account, Account):
            logger.info("%s.__init__(): received account %s", self.formatted_class_name, account)
            self._account = account
        if isinstance(user, User):
            self._user = user
            logger.info("%s.__init__(): received user %s", self.formatted_class_name, user)
            self._account = get_cached_account_for_user(user)
            if not self._account:
                logger.debug(
                    "%s.__init__(): did not find an account for user %s",
                    self.formatted_class_name,
                    user,
                )
            logger.info(
                "%s.__init__(): set account to %s based on user %s",
                self.formatted_class_name,
                self._account,
                self.user_profile,
            )

        # evaluate these in reverse order, so that the first one wins.
        if request is not None:
            url: str = self.smarter_build_absolute_uri(request)
            logger.debug("%s.__init__(): received a request object: %s", self.formatted_class_name, url)
            if hasattr(request, "user") and not isinstance(request.user, AnonymousUser):
                self._user = request.user  # type: ignore[union-attr]
                if not isinstance(self._user, User):
                    logger.debug(
                        "%s.__init__(): could not resolve user from the request object %s",
                        self.formatted_class_name,
                        request.build_absolute_uri(),
                    )
                logger.info(
                    "%s.__init__(): found a user object in the request: %s",
                    self.formatted_class_name,
                    self._user,
                )
                self._account = get_cached_account_for_user(self._user)
                if not isinstance(self._account, Account):
                    logger.debug(
                        "%s.__init__(): could not resolve account from the user %s",
                        self.formatted_class_name,
                        self._user,
                    )
                logger.info(
                    "%s.__init__(): set account to %s based on user: %s",
                    self.formatted_class_name,
                    self._account,
                    self.user_profile,
                )
            elif not api_token:
                logger.debug(
                    "%s.__init__(): did not find a user in the request object nor an Api token in the request header",
                    self.formatted_class_name,
                )
            if not self._account:
                # if the account is not set, then try to get it from the request
                # by parsing the URL.
                account_number = account_number_from_url(url)
                if account_number and waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_LOGGING):
                    logger.info(
                        "%s.__init__(): located account number %s from the request url %s",
                        self.formatted_class_name,
                        account_number,
                        url,
                    )
                    self._account = get_cached_account(account_number=account_number)
                    logger.info("%s.__init__(): set account to %s", self.formatted_class_name, self._account)
                elif not api_token:
                    logger.debug(
                        "%s.__init__(): did not find an account number in the request url nor an API token in the request header: %s",
                        self.formatted_class_name,
                        url,
                    )
        if not self._user and isinstance(api_token, bytes):
            logger.info(
                "%s.__init__(): found API token in kwargs: %s",
                self.formatted_class_name,
                mask_string(api_token.decode()),
            )
            user, _ = SmarterTokenAuthentication().authenticate_credentials(api_token)
            self.user = user

        if self.is_accountmixin_ready:
            logger.info(
                "%s.__init__(): is fully initialized with user: %s",
                self.formatted_class_name,
                self.user_profile,
            )

    def __str__(self):
        """
        Returns a string representation of the class.
        """
        return f"{self.__class__.__name__}(user={self.user_profile}, account={self._account})"

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class} AccountMixin()"

    @property
    def account(self) -> AccountType:
        """
        Returns the account for the current user. Handle
        lazy instantiation from user or user_profile.
        """
        try:
            if self._account:
                return self._account
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("error getting account: %s", e)
            return None
        if self._user_profile:
            self._account = self._user_profile.account if self._user_profile else None
        elif self._user:
            self._account = get_cached_account_for_user(self._user)
        return self._account

    @account.setter
    def account(self, account: AccountType):
        """
        Set the account for the current user. Handle
        management of user_profile.
        """
        if self._user:
            # If the user is already set, then we need to verify that the user is part of the account
            # by attempting to fetch the user_profile.
            try:
                self._user_profile = get_cached_user_profile(user=self._user, account=account)
            except UserProfile.DoesNotExist as e:
                raise SmarterBusinessRuleViolation(
                    f"User {self._user} does not belong to the account {self._account.account_number if isinstance(self._account, Account) else "unknown account"}."
                ) from e
            except TypeError as e:
                # TypeError: Field 'id' expected a number but got <SimpleLazyObject: <django.contrib.auth.models.AnonymousUser object at 0x70f8a5377c20>>.
                logger.error("%s: account not set, user_profile not found: %s", self.formatted_class_name, str(e))
        self._account = account
        if not self._account:
            # unset the user_profile if the account is unset
            self._user_profile = None
            return

    @property
    def account_number(self) -> AccountNumberType:
        """
        A helper function to get the account number from the account.
        """
        return self._account.account_number if self._account else None

    @account_number.setter
    def account_number(self, account_number: AccountNumberType):
        """
        A helper function to set the account from the account_number.
        """
        if not account_number:
            self._account = None
            self._user_profile = None
            return
        account = get_cached_account(account_number=account_number)
        if isinstance(account, Account):
            self._account = account
            logger.info(
                "%s: set account to %s based on account_number %s",
                self.formatted_class_name,
                self._account,
                account_number,
            )

    @property
    def user(self) -> UserType:
        """
        Returns the user for the current user. Handle
        lazy instantiation from user_profile or account.
        """
        try:
            if self._user:
                return self._user
        # pylint: disable=W0718
        except Exception as e:
            logger.warning("error getting user: %s", e)
            return None

        if self._user_profile:
            self._user = self._user_profile.user
        return self._user

    @user.setter
    def user(self, user: UserType):
        """
        Set the user for the current user. Handle
        management of user_profile, if the user is unset.
        Otherwise, initialize the account in which the user is contained.
        """
        if self._user and not user:
            # unset the user_profile and account if the user is unset
            self._user_profile = None
            self.account = None
            self._user = None
            return

        logger.info("%s.user.setter: %s", self.formatted_class_name, user)
        self._user = user
        if self._account and self._user:
            # If the account is already set, then we need to check if the user is part of the account
            # by attempting to fetch the user_profile.
            try:
                self._user_profile = get_cached_user_profile(user=self._user, account=self._account)
            except UserProfile.DoesNotExist as e:
                raise SmarterBusinessRuleViolation(
                    f"User {self._user} does not belong to the account {self._account.account_number}."
                ) from e
            except TypeError as e:
                # TypeError: Field 'id' expected a number but got <SimpleLazyObject: <django.contrib.auth.models.AnonymousUser object at 0x70f8a5377c20>>.
                logger.error("%s: account not set, user_profile not found: %s", self.formatted_class_name, str(e))
        else:
            self._user_profile = None

    @property
    def user_profile(self) -> UserProfileType:
        """
        Returns the user_profile for the current user. Handle
        lazy instantiation from user or account.
        """
        if self._user_profile:
            return self._user_profile
        # note that we have to use property references here in order to trigger
        # the property setters.
        if self._account and isinstance(self._user, User):
            try:
                self._user_profile = get_cached_user_profile(user=self._user, account=self._account)
                return self._user_profile
            except UserProfile.DoesNotExist as e:
                raise SmarterBusinessRuleViolation(
                    f"User {self._user} does not belong to the account {self._account.account_number}."
                ) from e
        if isinstance(self._user, User):
            self._user_profile = get_cached_user_profile(user=self._user)
        if not self._user_profile:
            logger.debug(
                "%s: user_profile() could not initialize _user_profile for user: %s, account: %s",
                self.formatted_class_name,
                self._user,
                self._account,
            )
        return self._user_profile

    @user_profile.setter
    def user_profile(self, user_profile: UserProfileType):
        """
        Set the user_profile for the current user. If we're unsetting the user_profile,
        then leave the user and account as they are. But if we're setting the user_profile,
        then set the user and account as well.
        """
        self._user_profile = user_profile
        if not self._user_profile:
            return
        self._user = self._user_profile.user
        self._account = self._user_profile.account

    @property
    def is_accountmixin_ready(self) -> bool:
        """
        Returns True if the AccountMixin is ready to be used.
        This is a convenience property that checks if the account and user
        are initialized.
        """
        if not isinstance(self.account, Account):
            logger.debug(
                "%s.is_accountmixin_ready() returning false because account is not initialized.",
                self.formatted_class_name,
            )
            return False
        if not isinstance(self.user, User):
            logger.debug(
                "%s.is_accountmixin_ready() returning false because user is not initialized.",
                self.formatted_class_name,
            )
            return False
        return True

    @property
    def ready(self) -> bool:
        """
        Returns True if the account and user are set.
        """
        retval = super().ready
        if not retval:
            logger.debug(
                "%s: ready() returning false because super().ready returned false. This might cause problems with other initializations.",
                self.formatted_class_name,
            )
        return retval and self.is_accountmixin_ready

    @property
    def is_authenticated(self) -> bool:
        """
        Returns True if the user is authenticated and is associated with an Account.
        """
        return bool(self._user) and self._user.is_authenticated and bool(self._account) and bool(self._user_profile)

    def to_json(self):
        """
        Returns a JSON representation of the account, user, and user_profile.
        """
        return {
            "ready": self.ready,
            "account": AccountMiniSerializer(self._account).data if self._account else None,
            "user": UserMiniSerializer(self._user).data if self._user else None,
            "user_profile": UserProfileSerializer(self.user_profile).data if self._user_profile else None,
            **super().to_json(),
        }
