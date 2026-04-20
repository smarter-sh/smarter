"""Connection app models."""

import logging
from abc import abstractmethod

from django.db import models

from smarter.apps.account.models import (
    MetaDataWithOwnershipModel,
    User,
    UserProfile,
)
from smarter.apps.account.utils import (
    get_cached_admin_user_for_account,
    smarter_cached_objects,
)
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.common.mixins import SmarterHelperMixin
from smarter.lib.cache import cache_results
from smarter.lib.django import waffle
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.logging import WaffleSwitchedLoggerWrapper


# pylint: disable=W0613
def should_log(level):
    """Check if logging should be done based on the waffle switch."""
    return waffle.switch_is_active(SmarterWaffleSwitches.CONNECTION_LOGGING)


base_logger = logging.getLogger(__name__)
logger = WaffleSwitchedLoggerWrapper(base_logger, should_log)
logger_prefix = formatted_text(f"{__name__}")


class ConnectionBase(MetaDataWithOwnershipModel, SmarterHelperMixin):
    """
    Abstract base class for all connection models in the Smarter platform.

    ``ConnectionBase`` defines the shared interface and core fields required for representing connection
    configurations to external data sources, such as SQL databases and remote APIs. This class is not
    intended to be instantiated directly, but rather to be subclassed by concrete connection models like
    :class:`SqlConnection` and :class:`ApiConnection`, each of which implements the logic for a specific
    connection type.

    This base class enforces a consistent structure for connection models by providing:
      - An ``account`` field to associate the connection with a specific user account.
      - A ``name`` field, validated to ensure snake_case and no spaces, for uniquely identifying the connection.
      - A ``kind`` field to distinguish between connection types (e.g., SQL, API).
      - Descriptive metadata fields such as ``description`` and ``version``.
      - An abstract ``connection_string`` property that must be implemented by subclasses to return a usable connection string.
      - Class methods for retrieving and caching connections for a user, supporting efficient access and management of connection objects.

    Subclasses are responsible for implementing the logic to establish, test, and manage connections to their
    respective data sources, as well as any additional configuration or validation required for their protocols.

    This class is foundational for the Smarter connection architecture, ensuring that all connection models
    adhere to a uniform interface and can be managed, validated, and retrieved in a consistent manner.

    See also:

    - :class:`smarter.apps.plugin.models.SqlConnection`
    - :class:`smarter.apps.plugin.models.ApiConnection`
    """

    CONNECTION_KIND_CHOICES = [
        (SAMKinds.SQL_CONNECTION.value, SAMKinds.SQL_CONNECTION.value),
        (SAMKinds.API_CONNECTION.value, SAMKinds.API_CONNECTION.value),
    ]

    kind = models.CharField(
        help_text="The kind of connection. Example: 'SQL', 'API'.",
        max_length=50,
        choices=CONNECTION_KIND_CHOICES,
    )

    @property
    def formatted_class_name(self) -> str:
        """
        Returns the class name formatted for logging.

        :return: The formatted class name as a string.
        :rtype: str

        """

        return formatted_text(self.__class__.__module__ + "." + self.__class__.__name__)

    @property
    @abstractmethod
    def connection_string(self) -> str:
        """Return the connection string."""
        raise NotImplementedError

    @classmethod
    @cache_results()
    def get_cached_connections_for_user(cls, user: User, invalidate: bool = False) -> list["ConnectionBase"]:
        """
        Return a list of all instances of all concrete subclasses of :class:`ConnectionBase`.

        This method retrieves all connection objects (such as :class:`SqlConnection` and :class:`ApiConnection`)
        associated with the user's account, across all concrete subclasses of :class:`ConnectionBase`.
        It is useful for enumerating all available connections for a given user, regardless of connection type.

        :param user: The user whose connections should be retrieved.
        :type user: User
        :return: A list of all connection instances for the user's account.
        :rtype: list[ConnectionBase]

        **Example:**

        .. code-block:: python

            connections = ConnectionBase.get_cached_connections_for_user(user)
            # returns [<SqlConnection ...>, <ApiConnection ...>, ...]

        See also:

        - :class:`SqlConnection`
        - :class:`ApiConnection`
        - :func:`smarter.apps.account.utils.get_cached_account_for_user`
        """
        if user is None:
            logger.warning("%s.get_cached_connections_for_user: user is None", cls.formatted_class_name)
            return []
        user_profile = UserProfile.get_cached_object(invalidate=invalidate, user=user)
        admin_user = get_cached_admin_user_for_account(invalidate=invalidate, account=user_profile.cached_account)  # type: ignore
        admin_user_profile = UserProfile.get_cached_object(invalidate=invalidate, user=admin_user)  # type: ignore
        instances = []
        for subclass in ConnectionBase.__subclasses__():
            instances.extend(subclass.objects.filter(user_profile=user_profile).order_by("name"))
            instances.extend(subclass.objects.filter(user_profile=admin_user_profile).order_by("name"))
            instances.extend(
                subclass.objects.filter(user_profile=smarter_cached_objects.smarter_admin_user_profile).order_by("name")
            )
        logger.debug(
            "%s.get_cached_connections_for_user: Found these connections %s for user %s",
            cls.formatted_class_name,
            instances,
            user,
        )
        unique_instances = {(instance.__class__, instance.pk): instance for instance in instances}.values()
        return list(unique_instances)


__all__ = [
    "ConnectionBase",
]
