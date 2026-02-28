# pylint: disable=W0613
"""A helper class that provides setters/getters for account and user."""

import logging
from typing import Optional, Union

from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed

from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.common.helpers.console_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import mask_string
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.token_authentication import (
    SmarterAnonymousUser,
    SmarterTokenAuthentication,
)
from smarter.lib.logging import WaffleSwitchedLoggerWrapper

from .models import Account, User, UserProfile
from .serializers import (
    AccountMiniSerializer,
    UserMiniSerializer,
    UserProfileSerializer,
)
from .utils import (
    account_number_from_url,
    get_cached_account,
    get_cached_account_for_user,
    get_cached_user_profile,
)

UserType = Union[AnonymousUser, User, None]
AccountNumberType = Optional[str]
ApiTokenType = Optional[bytes]


def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.ACCOUNT_MIXIN_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)


class AccountMixin(SmarterHelperMixin):
    """
    Provides consistent initialization and short-lived caching of the
    ``account``, ``user``, and ``user_profile`` properties using various sources,
    such as direct arguments, request objects, or API tokens. Also handles
    API token authentication when a request object with an Authorization
    header is provided.

    Initialization priority:

    1. API token authentication if provided.
    2. Explicit ``account_number``, ``account``, or ``user`` arguments.
    3. Request object (from ``kwargs`` or positional args), extracting user and account info.
    4. Lazy loading from existing ``user`` or ``user_profile``.
    5. User and Account parameters passed directly to the constructor.

    :param args: Positional arguments, may include a request object.
    :param account_number: Unique account identifier (optional).
    :type account_number: str or None
    :param account: Account instance (optional).
    :type account: Account or None
    :param user: Django user instance (optional).
    :type user: AnonymousUser, User, or None
    :param api_token: API token for authentication (optional).
    :type api_token: bytes or None
    :param kwargs: Additional keyword arguments, may include ``request``.

    The constructor attempts to resolve and cache the account and user information,
    logging relevant events and warnings if data cannot be resolved.
    """

    __slots__ = ("_account", "_user", "_user_profile")

    def __init__(
        self,
        *args,
        user: UserType = None,
        account: Optional[Account] = None,
        user_profile: Optional[UserProfile] = None,
        account_number: AccountNumberType = None,
        api_token: ApiTokenType = None,
        **kwargs,
    ):

        self._account: Optional[Account] = None
        self._user: UserType = None
        self._user_profile: Optional[UserProfile] = None
        super().__init__(*args, **kwargs)

        logger.debug(
            "%s.__init__() called with args=%s, user=%s, account=%s, user_profile=%s, account_number=%s, api_token=%s, kwargs=%s",
            self.account_mixin_logger_prefix,
            args,
            user,
            account,
            user_profile,
            account_number,
            mask_string(api_token.decode()) if api_token else None,
            kwargs,
        )

        # ---------------------------------------------------------------------
        # Initial resolution of parameters, taking into consideration that
        # they may be passed in via args or kwargs.
        # ---------------------------------------------------------------------
        request = kwargs.get("request") or next((arg for arg in args if "request" in str(type(arg)).lower()), None)
        user = user or kwargs.get("user", None) or next((arg for arg in args if isinstance(arg, User)), None)
        account = (
            account or kwargs.get("account", None) or next((arg for arg in args if isinstance(arg, Account)), None)
        )
        user_profile = (
            user_profile
            or kwargs.get("user_profile", None)
            or next((arg for arg in args if isinstance(arg, UserProfile)), None)
        )
        api_token = api_token or kwargs.get("api_token", None)

        if isinstance(account_number, str):
            logger.debug(
                "%s.__init__(): received account_number %s. This will take precedence over other account information",
                self.account_mixin_logger_prefix,
                account_number,
            )
            account = get_cached_account(account_number=account_number) if account_number else account

        # ---------------------------------------------------------------------
        # Process the request object if available. We're looking for any of
        # - account_number in the URL
        # - API token in the Authorization header
        # - user in the request object
        # ---------------------------------------------------------------------
        if request is not None:
            url: Optional[str] = self.smarter_build_absolute_uri(request)
            logger.debug(
                "%s.__init__(): received a request object: %s. This will take precedence over other information.",
                self.account_mixin_logger_prefix,
                url,
            )
            account_number = account_number or account_number_from_url(url)  # type: ignore[arg-type]
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Token "):
                if auth_header.split("Token ")[1].encode():
                    api_token = auth_header.split("Token ")[1].encode()
                    logger.debug(
                        "%s.__init__(): found API token in Authorization header of request object %s. This will take precedence over other information.",
                        self.account_mixin_logger_prefix,
                        mask_string(api_token.decode()),
                    )
            if not api_token and hasattr(request, "user") and not isinstance(request.user, AnonymousUser):
                user = request.user  # type: ignore[union-attr]
                if not isinstance(user, User):
                    logger.debug(
                        "%s.__init__(): could not resolve user from the request object %s",
                        self.account_mixin_logger_prefix,
                        request.build_absolute_uri(),
                    )
                logger.debug(
                    "%s.__init__(): found a user object in the request: %s. This will supersede other user information.",
                    self.account_mixin_logger_prefix,
                    user,
                )

        logger.debug(
            "%s.__init__(): resolved api_token=%s, account_number=%s, account=%s, user=%s, user_profile=%s",
            self.account_mixin_logger_prefix,
            mask_string(api_token.decode()) if api_token else None,
            account_number,
            account,
            user,
            user_profile,
        )

        # ---------------------------------------------------------------------
        # Final initialization based on priority order
        # ---------------------------------------------------------------------
        if isinstance(api_token, bytes):
            logger.debug(
                "%s.__init__(): found API token: %s. This will take precedence over other information.",
                self.account_mixin_logger_prefix,
                mask_string(api_token.decode()),
            )
            AccountMixin.authenticate(self, api_token)
        else:
            if user_profile:
                self.user_profile = user_profile
            elif user:
                self.user = user
                if account:
                    self.account = account
                    assert self.user_profile is not None
            elif account:
                self.account = account

        logger.debug(
            "%s.__init__() - finished %s",
            self.account_mixin_logger_prefix,
            AccountMixin.__repr__(self),
        )

        self.log_account_mixin_ready_status()

    def __str__(self):
        """
        Returns a string representation of the class.

        :return: String representation of the class.
        :rtype: str
        """
        return f"{formatted_text(AccountMixin.__name__)}[{id(self)}](user_profile={self.user_profile})"

    def __repr__(self) -> str:
        """
        Returns a JSON representation of the class.

        :return: JSON representation of the class.
        :rtype: str
        """
        return self.__str__()

    def __bool__(self) -> bool:
        """
        Returns True if the AccountMixin is ready to be used.

        :return: True if the AccountMixin is ready to be used.
        :rtype: bool
        """
        return self.is_accountmixin_ready

    def __hash__(self) -> int:
        """
        Returns the hash of the user_profile.

        :return: Hash of the user_profile.
        :rtype: int
        """
        return hash(self.user_profile)

    def __eq__(self, value: object) -> bool:
        """
        Returns True if the user_profile is the same.

        :param value: The value to compare to.
        :type value: object
        :return: True if the user_profile is the same.
        :rtype: bool
        """
        return isinstance(value, AccountMixin) and self.user_profile == value.user_profile

    def __lt__(self, value: object) -> bool:
        """
        Returns True if the user_profile is less than the other user_profile.

        :param value: The value to compare to.
        :type value: object
        :return: True if the user_profile is less than the other user_profile.
        :rtype: bool
        """
        if not isinstance(value, AccountMixin):
            return NotImplemented
        # Compare by user_profile id if both exist, else handle None
        self_profile = self.user_profile
        other_profile = value.user_profile
        if self_profile is None and other_profile is None:
            return False
        if self_profile is None:
            return True  # None is considered less than any profile
        if other_profile is None:
            return False

        return str(self_profile) < str(other_profile)

    def __le__(self, value: object) -> bool:
        """
        Returns True if the user_profile is less than or equal to the other user_profile.

        :param value: The value to compare to.
        :type value: object
        :return: True if the user_profile is less than or equal to the other user_profile.
        :rtype: bool
        """
        if not isinstance(value, AccountMixin):
            return NotImplemented
        return self == value or self < value

    def __gt__(self, value: object) -> bool:
        """
        Returns True if the user_profile is greater than the other user_profile.

        :param value: The value to compare to.
        :type value: object
        :return: True if the user_profile is greater than the other user_profile.
        :rtype: bool
        """
        if not isinstance(value, AccountMixin):
            return NotImplemented
        return not self <= value

    def __ge__(self, value: object) -> bool:
        """
        Returns True if the user_profile is greater than or equal to the other user_profile.

        :param value: The value to compare to.
        :type value: object
        :return: True if the user_profile is greater than or equal to the other user_profile
        :rtype: bool
        """
        if not isinstance(value, AccountMixin):
            return NotImplemented
        return not self < value

    @property
    def account_mixin_logger_prefix(self) -> str:
        """
        Returns the logger prefix for the class.
        """
        return formatted_text(f"{__name__}.{AccountMixin.__name__}[{id(self)}]")

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name in a formatted string
        along with the name of this mixin.
        """
        inherited_class = super().formatted_class_name
        return f"{inherited_class} {AccountMixin.__name__}[{id(self)}]"

    @property
    def account(self) -> Optional[Account]:
        """
        Returns the account for the current user. Handle
        lazy instantiation from user or user_profile.

        :return: The account for the current user.
        :rtype: Account or None
        """
        if self._account:
            return self._account
        if isinstance(self._user_profile, UserProfile):
            self._account = self._user_profile.account
            logger.debug(
                "%s.account() set _account to %s based on user_profile %s",
                self.account_mixin_logger_prefix,
                self._account,
                self._user_profile,
            )
            return self._account
        if self._user:
            self._account = get_cached_account_for_user(self._user)
            if self._account:
                logger.debug(
                    "%s.account() set _account to %s based on user %s",
                    self.account_mixin_logger_prefix,
                    self._account,
                    self._user,
                )
            return self._account
        logger.debug(
            "%s.account() could not initialize _account for user: %s, user_profile: %s",
            self.account_mixin_logger_prefix,
            self._user,
            self._user_profile,
        )
        return None

    @account.setter
    def account(self, account: Optional[Account]):
        """
        Set the account for the current user. Handle
        management of user_profile.
        """
        self._account = account
        logger.debug("%s.account.setter: set _account to %s", self.account_mixin_logger_prefix, self._account)
        self._user_profile = None
        logger.debug("%s.account.setter: reset _user_profile to None", self.account_mixin_logger_prefix)
        if not account:
            return

        if self.user:
            # If the user is already set, then we need to verify that the user is part of the account
            # by attempting to fetch the user_profile.
            self._user_profile = get_cached_user_profile(user=self.user, account=account)  # type: ignore[arg-type]
            if not self._user_profile:
                raise SmarterBusinessRuleViolation(
                    f"User {self._user} is not associated with the account {self._account.account_number if isinstance(self._account, Account) else "unknown account"}."
                )

            logger.debug(
                "%s.account.setter: set _user_profile to %s based on user %s and account %s",
                self.account_mixin_logger_prefix,
                self._user_profile,
                self._user,
                self._account,
            )
            self.log_account_mixin_ready_status()

    @property
    def account_number(self) -> AccountNumberType:
        """
        A helper function to get the account number from the account.

        :return: The account number for the current account.
        :rtype: str or None
        """
        return self._account.account_number if self._account else None

    @account_number.setter
    def account_number(self, account_number: AccountNumberType):
        """
        A helper function to set the account from the account_number.

        :param account_number: The account number to set the account from.
        :type account_number: str or None
        :return: None
        :rtype: None
        """
        if not account_number:
            self._account = None
            logger.debug("%s.account_number.setter: unset _account", self.account_mixin_logger_prefix)
            self._user_profile = None
            logger.debug("%s.account_number.setter: unset _user_profile", self.account_mixin_logger_prefix)
            return
        account = get_cached_account(account_number=account_number)
        if isinstance(account, Account):
            self._account = account
            logger.debug(
                "%s: set account to %s based on account_number %s",
                self.account_mixin_logger_prefix,
                self._account,
                account_number,
            )
            self.log_account_mixin_ready_status()

    @property
    def user(self) -> UserType:
        """
        Returns the user for the current user. Handle
        lazy instantiation from user_profile or account.

        :return: The user for the current user.
        :rtype: User or None
        """
        if self._user:
            return self._user

        if self._user_profile:
            self._user = self._user_profile.user
            logger.debug(
                "%s.user() set _user to %s based on user_profile %s",
                self.account_mixin_logger_prefix,
                self._user,
                self._user_profile,
            )
        return self._user

    @user.setter
    def user(self, user: UserType):
        """
        Set the user.

        :param user: The user to set.
        :type user: User or None
        :return: None
        :rtype: None
        """
        self._user = user
        if not user:
            self._account = None
            logger.debug("%s.user.setter: unset _account", self.account_mixin_logger_prefix)
            self._user_profile = None
            logger.debug("%s.user.setter: unset _user_profile", self.account_mixin_logger_prefix)
            return
        self.log_account_mixin_ready_status()

    @property
    def user_profile(self) -> Optional[UserProfile]:
        """
        Returns the user_profile for the current user. Handle
        lazy instantiation from user or account.

        :return: The user_profile for the current user.
        :rtype: UserProfile or None
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
                self.account_mixin_logger_prefix,
                self._user,
                self._account,
            )
        else:
            self.log_account_mixin_ready_status()
        return self._user_profile

    @user_profile.setter
    def user_profile(self, user_profile: Optional[UserProfile]):
        """
        Set the user_profile for the current user. If we're unsetting the user_profile,
        then leave the user and account as they are. But if we're setting the user_profile,
        then set the user and account as well.

        :param user_profile: The user_profile to set.
        :type user_profile: UserProfile or None
        :return: None
        :rtype: None
        """
        self._user_profile = user_profile
        logger.debug(
            "%s.user_profile.setter: set _user_profile to %s", self.account_mixin_logger_prefix, self._user_profile
        )
        if not self._user_profile:
            self._user = None
            logger.debug("%s.user_profile.setter: unset _user", self.account_mixin_logger_prefix)
            self._account = None
            logger.debug("%s.user_profile.setter: unset _account", self.account_mixin_logger_prefix)
        else:
            self._user = self._user_profile.user
            logger.debug("%s.user_profile.setter: set _user to %s", self.account_mixin_logger_prefix, self._user)
            self._account = self._user_profile.account
            logger.debug("%s.user_profile.setter: set _account to %s", self.account_mixin_logger_prefix, self._account)
            self.log_account_mixin_ready_status()

    @property
    def is_accountmixin_ready(self) -> bool:
        """
        Returns True if the AccountMixin is ready to be used.
        This is a convenience property that checks if the account and user
        are initialized. AccountMixin is considered ready if:
        - self.user is an instance of User
        - self.user_profile is an instance of UserProfile
        - self.account is an instance of Account

        :return: True if the AccountMixin is ready to be used.
        :rtype: bool
        """
        if not isinstance(self.user_profile, UserProfile):
            logger.debug(
                "%s.is_accountmixin_ready() returning false because user_profile is not initialized.",
                self.account_mixin_logger_prefix,
            )
            return False
        if not isinstance(self.user, User):
            logger.debug(
                "%s.is_accountmixin_ready() had to initialize user from user_profile. This is a bug.",
                self.account_mixin_logger_prefix,
            )
            self._user = self.user_profile.user
        if not isinstance(self.account, Account):
            logger.debug(
                "%s.is_accountmixin_ready() had to initialize account from user_profile. This is a bug.",
                self.account_mixin_logger_prefix,
            )
            self._account = self.user_profile.account
        logger.debug("%s.is_accountmixin_ready() returning true.", self.account_mixin_logger_prefix)
        return True

    @property
    def accountmixin_ready_state(self) -> str:
        """
        Returns a string representation of the AccountMixin ready state.

        :return: String representation of the AccountMixin ready state.
        :rtype: str
        """
        if self.is_accountmixin_ready:
            return self.formatted_state_ready
        else:
            return self.formatted_state_not_ready

    @property
    def ready(self) -> bool:
        """
        Returns True if the account and user are set.
        """
        retval = SmarterHelperMixin(self).ready
        if not retval:
            logger.debug(
                "%s: ready() returning false because super().ready returned false. This might cause problems with other initializations.",
                self.account_mixin_logger_prefix,
            )
        return retval and self.is_accountmixin_ready

    @property
    def ready_state(self) -> str:
        """
        Returns a string representation of the ready state.
        """
        if self.is_accountmixin_ready:
            return self.formatted_state_ready
        else:
            return self.formatted_state_not_ready

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
        return self.sorted_dict(
            {
                "ready": self.is_accountmixin_ready,
                "account": AccountMiniSerializer(self.account).data if self.account else None,
                "user": UserMiniSerializer(self.user).data if self.user else None,
                "user_profile": UserProfileSerializer(self.user_profile).data if self.user_profile else None,
                **SmarterHelperMixin(self).to_json(),
            }
        )

    def authenticate(self, api_token: bytes) -> bool:
        """
        Authenticate the user using the provided API token. The api_token will
        have been generated by the SmarterTokenAuthentication class and passed
        by the caller in the Authorization header of the request.

        example:
            Authorization: Token <api_token>

        :param api_token: The API token to authenticate with.
        :type api_token: bytes
        :return: True if authentication was successful, False otherwise.
        :rtype: bool
        """
        logger.debug(
            "%s.authenticate() called with api_token=%s",
            self.account_mixin_logger_prefix,
            mask_string(api_token.decode()),
        )
        try:
            user, _ = SmarterTokenAuthentication().authenticate_credentials(api_token)
            self.user = user
            return True
        except AuthenticationFailed:
            self.user = SmarterAnonymousUser()
            logger.warning(
                "%s.authenticate(): failed to authenticate user from API token", self.account_mixin_logger_prefix
            )
        return False

    def log_account_mixin_ready_status(self):
        """
        Logs the ready status of the AccountMixin.
        """
        msg = f"{self.account_mixin_logger_prefix} is {self.accountmixin_ready_state} - {self.user_profile}"
        if self.is_accountmixin_ready:
            logger.info(msg)
        else:
            logger.debug(msg)
