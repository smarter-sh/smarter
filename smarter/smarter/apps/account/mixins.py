# pylint: disable=W0613
"""A helper class that provides setters/getters for account and user."""

from typing import Optional, Union

from django.contrib.auth.models import AnonymousUser
from rest_framework.exceptions import AuthenticationFailed

from smarter.common.exceptions import SmarterBusinessRuleViolation
from smarter.common.mixins import SmarterHelperMixin
from smarter.common.utils import mask_string
from smarter.lib import logging
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.token_authentication import (
    SmarterAnonymousUser,
    SmarterTokenAuthentication,
)

from .models import Account, User, UserProfile
from .models.budget import charge_authorization
from .serializers import (
    AccountMiniSerializer,
    UserMiniSerializer,
    UserProfileSerializer,
)
from .utils import (
    account_number_from_url,
    get_cached_account_for_user,
)

UserType = Union[AnonymousUser, User, None]
AccountNumberType = Optional[str]
ApiTokenType = Optional[bytes]


logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.ACCOUNT_MIXIN_LOGGING])


class AccountMixin(SmarterHelperMixin):
    """
    Provides consistent initialization and short-lived caching of the.

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

    __slots__ = ("_account", "_user", "_user_profile", "_am_ready")

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
        self._am_ready: bool = False
        super().__init__(*args, **kwargs)

        logger.debug(
            "%s.__init__() called with args=%s, user=%s, account=%s, user_profile=%s, account_number=%s, api_token=%s, kwargs=%s",
            self._am_formatted_class_name,
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
                self._am_formatted_class_name,
                account_number,
            )
            account = Account.get_cached_object(account_number=account_number)

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
                self._am_formatted_class_name,
                url,
            )
            account_number = account_number or account_number_from_url(url)  # type: ignore[arg-type]
            auth_header = request.headers.get("Authorization", "")
            if auth_header.startswith("Token "):
                if auth_header.split("Token ")[1].encode():
                    api_token = auth_header.split("Token ")[1].encode()
                    logger.debug(
                        "%s.__init__(): found API token in Authorization header of request object %s. This will take precedence over other information.",
                        self._am_formatted_class_name,
                        mask_string(api_token.decode()) if isinstance(api_token, (bytes, bytearray)) else None,
                    )
            if not api_token and hasattr(request, "user") and not isinstance(request.user, AnonymousUser):
                user = request.user  # type: ignore[union-attr]
                if isinstance(user, User):
                    logger.debug(
                        "%s.__init__(): found a user object in the request: %s. This will supersede other user information.",
                        self._am_formatted_class_name,
                        user,
                    )
                else:
                    logger.debug(
                        "%s.__init__(): could not resolve user from the request object %s",
                        self._am_formatted_class_name,
                        request.build_absolute_uri(),
                    )
                    user = None

        logger.debug(
            "%s.__init__(): resolved api_token=%s, account_number=%s, account=%s, user=%s, user_profile=%s",
            self._am_formatted_class_name,
            mask_string(api_token.decode()) if isinstance(api_token, (bytes, bytearray)) else None,
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
                self._am_formatted_class_name,
                mask_string(api_token.decode()),
            )
            AccountMixin.authenticate(self, api_token)
        else:
            if user_profile:
                logger.debug(
                    "%s.__init__(): found a user_profile object: %s. This will take precedence over other information.",
                    self._am_formatted_class_name,
                    user_profile,
                )
                self.user_profile = user_profile
            elif user and account:
                logger.debug(
                    "%s.__init__(): found a user and account: %s, %s. This will take precedence over other information.",
                    self._am_formatted_class_name,
                    user,
                    account,
                )
                self.user_profile = UserProfile.get_cached_object(user=user, account=account)  # type: ignore
            elif user and not self.user:
                logger.debug(
                    "%s.__init__(): found a user object: %s. This will take precedence over other information.",
                    self._am_formatted_class_name,
                    user,
                )
                self.user = user
            elif account and not self.account:
                logger.debug(
                    "%s.__init__(): found an account object: %s. This will take precedence over other information.",
                    self._am_formatted_class_name,
                    account,
                )
                self.account = account

        logger.debug(
            "%s.__init__() - finished %s",
            self._am_formatted_class_name,
            AccountMixin.__repr__(self),
        )

        self._am_log_ready_status()

    def __str__(self):
        """
        Returns a string representation of the class.

        :return: String representation of the class.
        :rtype: str
        """
        return f"{logging.formatted_text(AccountMixin.__name__)}[{id(self)}](user_profile={self.user_profile})"

    def __repr__(self) -> str:
        """
        Returns a JSON representation of the class.

        :return: JSON representation of the class.
        :rtype: str
        """
        return self.__str__()

    def __bool__(self) -> bool:
        """
        Returns True if the AccountMixin is am_ready to be used.

        :return: True if the AccountMixin is am_ready to be used.
        :rtype: bool
        """
        return self.am_ready

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

    def init(self, *args, **kwargs) -> None:
        """
        An optional method that can be called after initialization to perform any additional setup.

        This is separate from __init__ to allow for more flexible initialization patterns.

        :param args: Positional arguments passed to the init method.
        :param kwargs: Keyword arguments passed to the init method.
        :return: None
        """
        logger.debug(
            "%s.init() called with args: %s, kwargs: %s",
            self._am_formatted_class_name,
            args,
            kwargs,
        )
        if not self.am_ready:
            user = kwargs.get("user", None)
            account = kwargs.get("account", None)
            user_profile = kwargs.get("user_profile", None)
            if user_profile:
                self.user_profile = user_profile
            elif user and account:
                self.user_profile = UserProfile.get_cached_object(user=user, account=account)  # type: ignore
            elif user and not self.user:
                self.user = user
            elif account and not self.account:
                self.account = account
            self._am_log_ready_status()

    def setup(self, *args, **kwargs) -> None:
        """
        This method is called by Django views during initialization.

        It attempts to resolve the account and user information from the request object if it hasn't already been set.

        :param args: Positional arguments passed to the view.
        :param kwargs: Keyword arguments passed to the view, may include 'request'.
        :return: The result of the superclass setup method.
        :rtype: None
        """
        logger.debug(
            "%s.setup() called with args: %s, kwargs: %s",
            self._am_formatted_class_name,
            args,
            kwargs,
        )
        if not self.am_ready:
            self.init(*args, **kwargs)
        logger.debug(
            "%s.setup() completed with args: %s, kwargs: %s",
            self._am_formatted_class_name,
            args,
            kwargs,
        )

    @property
    def _am_formatted_class_name(self) -> str:
        """Returns the logger prefix for the class."""
        class_name = f"{__name__}.{AccountMixin.__name__}[{id(self)}]"
        return self.formatted_text(class_name)

    @property
    def account(self) -> Optional[Account]:
        """
        Returns the account for the current user.

        Handle
        lazy instantiation from user or user_profile.

        :return: The account for the current user.
        :rtype: Account or None
        """
        try:
            if self._account:
                return self._account
            if isinstance(self._user_profile, UserProfile):
                self._account = self._user_profile.account
                logger.debug(
                    "%s.account() set _account to %s based on user_profile %s",
                    self._am_formatted_class_name,
                    self._account,
                    self._user_profile,
                )
                return self._account
            if self._user:
                try:
                    self._account = get_cached_account_for_user(invalidate=False, user=self._user)  # type: ignore[assignment]
                except Account.DoesNotExist as e:
                    logger.error(
                        "%s.account() could not find an account for user %s during lazy loading. This should not happen.",
                        self._am_formatted_class_name,
                        self._user,
                    )
                    raise SmarterBusinessRuleViolation(
                        f"Could not find an account for user {self._user} during lazy loading."
                    ) from e
                except Account.MultipleObjectsReturned:
                    logger.info(
                        "%s.account() found multiple accounts for user %s during lazy loading. Cannot lazily initialize account from UserProfile.",
                        self._am_formatted_class_name,
                        self._user,
                    )
                    return (
                        self._account
                    )  # if there are multiple accounts then we're unable to lazily set from UserProfile

                if self._account:
                    logger.debug(
                        "%s.account() set _account to %s based on user %s",
                        self._am_formatted_class_name,
                        self._account,
                        self._user,
                    )
                    try:
                        self._user_profile = UserProfile.get_cached_object(user=self._user, account=self._account)  # type: ignore[assignment]
                        self._am_ready = True
                        logger.debug(
                            "%s.account() lazily set _user_profile to %s",
                            self._am_formatted_class_name,
                            self._user_profile,
                        )
                        self._am_log_ready_status()
                    except UserProfile.DoesNotExist as e:
                        logger.error(
                            "%s.account() could not find a user_profile for user %s and account %s during lazy loading. This should not happen.",
                            self._am_formatted_class_name,
                            self._user,
                            self._account,
                        )
                        raise SmarterBusinessRuleViolation(
                            f"Could not find a user_profile for user {self._user} and account {self._account} during lazy loading."
                        ) from e
                return self._account
            logger.debug(
                "%s.account() could not initialize _account for user: %s, user_profile: %s",
                self._am_formatted_class_name,
                self._user,
                self._user_profile,
            )
            return None
        except AttributeError as e:
            logger.error(
                "%s.account() AccountMixin appears to be only partially initialized: %s",
                self._am_formatted_class_name,
                e,
                exc_info=True,
            )
            return None
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.account() encountered an error while trying to resolve account: %s",
                self._am_formatted_class_name,
                e,
                exc_info=True,
            )
            return None

    @account.setter
    def account(self, account: Optional[Account]):
        """
        Set the account for the current user.

        Handle
        management of user_profile.
        """
        if isinstance(self._account, Account) and account is not None:
            raise SmarterBusinessRuleViolation(f"Account is already set to {self._account}. It is now immutable.")
        self._account = account
        logger.debug("%s.account.setter: set _account to %s", self._am_formatted_class_name, self._account)
        self._user_profile = None
        logger.debug("%s.account.setter: reset _user_profile to None", self._am_formatted_class_name)
        if not account:
            return

        if self.user:
            # If the user is already set, then we need to verify that the user is part of the account
            # by attempting to fetch the user_profile.
            try:
                self._user_profile = UserProfile.get_cached_object(invalidate=False, user=self.user, account=account)  # type: ignore[arg-type]
                self._am_ready = True
                logger.debug(
                    "%s.account.setter: lazily set _user_profile to %s",
                    self._am_formatted_class_name,
                    self._user_profile,
                )
                self._am_log_ready_status()
            except UserProfile.DoesNotExist as e:
                raise SmarterBusinessRuleViolation(
                    f"User {self._user} is not associated with the account {account.account_number}."
                ) from e
            # this should actually happen.
            if not self._user_profile:
                raise SmarterBusinessRuleViolation(
                    f"User {self._user} is not associated with the account {self._account.account_number if isinstance(self._account, Account) else "unknown account"}."
                )

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
        if isinstance(self._account, Account):
            raise SmarterBusinessRuleViolation(f"Account is already set to {self._account}. It is now immutable.")
        if not account_number:
            self._account = None
            logger.debug("%s.account_number.setter: unset _account", self._am_formatted_class_name)
            self._user_profile = None
            logger.debug("%s.account_number.setter: unset _user_profile", self._am_formatted_class_name)
            return
        account = Account.get_cached_object(account_number=account_number)
        if isinstance(account, Account):
            self._account = account
            logger.debug(
                "%s: set account to %s based on account_number %s",
                self._am_formatted_class_name,
                self._account,
                account_number,
            )

    @property
    def user(self) -> UserType:
        """
        Returns the user.

        Handle lazy instantiation from user_profile or account.

        :return: The user.
        :rtype: User or None
        """
        try:
            if self._user:
                return self._user

            if self._user_profile:
                self._user = self._user_profile.user
                logger.debug(
                    "%s.user() set _user to %s based on user_profile %s",
                    self._am_formatted_class_name,
                    self._user,
                    self._user_profile,
                )
            return self._user
        except AttributeError as e:
            logger.error(
                "%s.account() AccountMixin appears to be only partially initialized: %s",
                self._am_formatted_class_name,
                e,
                exc_info=True,
            )
            return None
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.user() encountered an error while trying to resolve user: %s",
                self._am_formatted_class_name,
                e,
                exc_info=True,
            )
            return None

    @user.setter
    def user(self, user: UserType):
        """
        Set the user.

        :param user: The user to set.
        :type user: User or None
        :return: None
        :rtype: None
        """
        if isinstance(self._user, User):
            raise SmarterBusinessRuleViolation(f"User is already set to {self._user}. It is now immutable.")
        self._user = user
        logger.debug("%s.user.setter: set user to %s", self._am_formatted_class_name, self._user)
        if not user:
            self._account = None
            logger.debug("%s.user.setter: unset _account", self._am_formatted_class_name)
            self._user_profile = None
            logger.debug("%s.user.setter: unset _user_profile", self._am_formatted_class_name)
            return
        try:
            self._user_profile = UserProfile.get_cached_object(user=user)  # type: ignore[assignment]
            self._am_ready = True
            logger.debug(
                "%s.user.setter: lazily set _user_profile to %s based on user %s",
                self._am_formatted_class_name,
                self._user_profile,
                self._user,
            )
            self._am_log_ready_status()
        except UserProfile.DoesNotExist as e:
            raise SmarterBusinessRuleViolation(f"User {self._user} does not belong to any account.") from e
        except UserProfile.MultipleObjectsReturned:
            logger.info(
                "%s.user.setter: found multiple user_profiles for user %s during lazy loading. Cannot lazily initialize user_profile from User.",
                self._am_formatted_class_name,
                self._user,
            )

    @property
    def user_profile(self) -> Optional[UserProfile]:
        """
        Returns the user_profile for the current user.

        Handle
        lazy instantiation from user or account.

        :return: The user_profile for the current user.
        :rtype: UserProfile or None
        """
        try:
            if self._user_profile:
                self._am_ready = True
                return self._user_profile
            # note that we have to use property references here in order to trigger
            # the property setters.
            if self._account and isinstance(self._user, User):
                try:
                    self._user_profile = UserProfile.get_cached_object(user=self._user, account=self._account)
                    self._am_ready = True
                    logger.debug(
                        "%s.user_profile() lazily set _user_profile to %s based on user %s and account %s",
                        self._am_formatted_class_name,
                        self._user_profile,
                        self._user,
                        self._account,
                    )
                    self._am_log_ready_status()
                    return self._user_profile
                except UserProfile.DoesNotExist as e:
                    raise SmarterBusinessRuleViolation(
                        f"User {self._user} does not belong to the account {self._account.account_number}."
                    ) from e
            if isinstance(self._user, User):
                self._user_profile = UserProfile.get_cached_object(user=self._user)
                self._am_ready = True
                logger.debug(
                    "%s.user_profile() lazily set _user_profile to %s",
                    self._am_formatted_class_name,
                    self._user_profile,
                )
                self._am_log_ready_status()
            if not self._user_profile:
                logger.debug(
                    "%s: user_profile() could not initialize _user_profile for user: %s, account: %s",
                    self._am_formatted_class_name,
                    self._user,
                    self._account,
                )
            else:
                self._am_ready = True
                self._am_log_ready_status()
            return self._user_profile
        except AttributeError as e:
            logger.error(
                "%s.account() AccountMixin appears to be only partially initialized: %s",
                self._am_formatted_class_name,
                e,
                exc_info=True,
            )
            return None
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.user_profile() encountered an error while trying to resolve user_profile: %s",
                self._am_formatted_class_name,
                e,
                exc_info=True,
            )
            return None

    @user_profile.setter
    def user_profile(self, user_profile: Optional[UserProfile]):
        """
        Set the user_profile for the current user.

        If we're unsetting the user_profile,
        then leave the user and account as they are. But if we're setting the user_profile,
        then set the user and account as well.

        :param user_profile: The user_profile to set.
        :type user_profile: UserProfile or None
        :return: None
        :rtype: None
        """
        if isinstance(self._user_profile, UserProfile):
            raise SmarterBusinessRuleViolation(
                f"UserProfile is already set to {self._user_profile}. It is now immutable."
            )
        self._user_profile = user_profile
        logger.debug(
            "%s.user_profile.setter: set _user_profile to %s", self._am_formatted_class_name, self._user_profile
        )
        if not self._user_profile:
            self._user = None
            logger.debug("%s.user_profile.setter: unset _user", self._am_formatted_class_name)
            self._account = None
            logger.debug("%s.user_profile.setter: unset _account", self._am_formatted_class_name)
        else:
            self._user = self._user_profile.user
            logger.debug("%s.user_profile.setter: set _user to %s", self._am_formatted_class_name, self._user)
            self._account = self._user_profile.account
            logger.debug("%s.user_profile.setter: set _account to %s", self._am_formatted_class_name, self._account)
            self._am_ready = True
            self._am_log_ready_status()

    @property
    def am_ready(self) -> bool:
        """
        Returns True if the AccountMixin is am_ready to be used.

        This is a convenience property that checks if the account and user
        are initialized. AccountMixin is considered am_ready if:
        - self.user is an instance of User
        - self.user_profile is an instance of UserProfile
        - self.account is an instance of Account

        :return: True if the AccountMixin is am_ready to be used.
        :rtype: bool
        """
        if self._am_ready:
            return True
        try:
            if not super().ready:
                logger.debug(
                    "%s.am_ready() returning false because superclass is not ready.",
                    self._am_formatted_class_name,
                )
                return False
            if not isinstance(self.user_profile, UserProfile):
                logger.debug(
                    "%s.am_ready() returning false because user_profile is not initialized.",
                    self._am_formatted_class_name,
                )
                return False
            if not isinstance(self.user, User):
                logger.debug(
                    "%s.am_ready() had to initialize user from user_profile. This is a bug.",
                    self._am_formatted_class_name,
                )
                self._user = self.user_profile.cached_user
            if not isinstance(self.account, Account):
                logger.debug(
                    "%s.am_ready() had to initialize account from user_profile. This is a bug.",
                    self._am_formatted_class_name,
                )
                self._account = self.user_profile.cached_account
            charge_authorization(self.user_profile.record_locator, self.__class__.__name__)
            charge_authorization(self.user_profile.account.record_locator, self.__class__.__name__)
            self._am_ready = True
            self._am_log_ready_status()
            return self._am_ready
        except AttributeError as e:
            logger.error(
                "%s.account() AccountMixin appears to be only partially initialized. This is a bug: %s",
                self._am_formatted_class_name,
                e,
                exc_info=True,
            )
            return False
        # pylint: disable=broad-except
        except Exception as e:
            logger.error(
                "%s.am_ready() encountered an error while checking am_ready state. This is a bug: %s",
                self._am_formatted_class_name,
                e,
                exc_info=True,
            )
            return False

    @property
    def _am_ready_state(self) -> str:
        """
        Returns a string representation of the AccountMixin am_ready state.

        :return: String representation of the AccountMixin am_ready state.
        :rtype: str
        """
        if self.am_ready:
            return self.formatted_state_ready
        else:
            return self.formatted_state_not_ready

    @property
    def ready_state(self) -> str:
        """Returns a string representation of the am_ready state."""
        if self.am_ready:
            return self.formatted_state_ready
        else:
            return self.formatted_state_not_ready

    @property
    def is_authenticated(self) -> bool:
        """Returns True if the user is authenticated and is associated with an Account."""
        return bool(self._user) and self._user.is_authenticated and bool(self._account) and bool(self._user_profile)

    def to_json(self):
        """Returns a JSON representation of the account, user, and user_profile."""
        return self.sorted_dict(
            {
                "am_ready": self.am_ready,
                "account": AccountMiniSerializer(self.account).data if self.account else None,
                "user": UserMiniSerializer(self.user).data if self.user else None,
                "userProfile": UserProfileSerializer(self.user_profile).data if self.user_profile else None,
            }
        )

    def authenticate(self, api_token: bytes) -> bool:
        """
        Authenticate the user using the provided API token.

        The api_token will
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
            self._am_formatted_class_name,
            mask_string(api_token.decode()),
        )
        try:
            user, _ = SmarterTokenAuthentication().authenticate_credentials(api_token)
            self._user = user
            self._account = None
            self._user_profile = None
            logger.debug(
                "%s.authenticate(): successfully authenticated user %s from API token.",
                self._am_formatted_class_name,
                self._user,
            )
            return True
        except AuthenticationFailed:
            self._user = SmarterAnonymousUser()
            self._account = None
            self._user_profile = None
            logger.warning(
                "%s.authenticate(): failed to authenticate user from API token", self._am_formatted_class_name
            )
        return False

    def log_ready_status(self):
        """Logs the ready status of the view."""
        msg = f"{self.formatted_class_name} is {self.ready_state}"
        logger.info(msg)

    def _am_log_ready_status(self):
        """Logs the am_ready status of the AccountMixin."""
        msg = f"{self._am_formatted_class_name} is {self._am_ready_state}"
        logger.info(msg)
