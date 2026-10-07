"""LLMClientAPIKey model for managing API keys associated with LLMClient instances in the Smarter platform."""

from typing import Optional

from django.db import models

from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken

from .llmclient import LLMClient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


class LLMClientAPIKey(TimestampedModel):
    """
    Represents the mapping of API keys to LLMClient instances within the Smarter platform.

    .. important::

        If present, the LLMClient associated with this record will require Api Key authentication
        for all API requests. Otherwise, the LLMClient will allow anonymous unauthenticated access.

        See :class:`smarter.lib.drf.token_authentication.SmarterTokenAuthentication` .

    This model establishes a relationship between a LLMClient and its associated API keys,
    enabling secure authentication and authorization for API access. Each entry in this
    model links a specific LLMClient to a unique API key, allowing fine-grained control
    over which keys can interact with which llmclient instances.

    The LLMClientAPIKey model is essential for managing access to llmclient APIs, supporting
    use cases such as per-bot API key rotation, revocation, and auditing. By associating
    API keys with individual llmclients, the platform can enforce security policies and
    monitor usage at the llmclient level.

    Typical usage involves creating a LLMClientAPIKey instance whenever a new API key is
    provisioned for an llmclient, and querying this model to validate incoming requests
    against active keys.

    **Model Relationships**

    - Each LLMClientAPIKey is linked to one :class:`LLMClient` instance.
    - Each LLMClientAPIKey references one :class:`SmarterAuthToken` representing the API key.

    **Example**

    .. code-block:: python

        # Assign an API key to an llmclient
        api_key = SmarterAuthToken.objects.create(...)
        llmclient_api_key = LLMClientAPIKey.objects.create(llmclient=my_llmclient, api_key=api_key)

        # Query API keys for an llmclient
        keys = LLMClientAPIKey.objects.filter(llmclient=my_llmclient)

    **Notes**

    - API key activation and deactivation are managed via the SmarterAuthToken model.
    - This model supports auditing and access control for llmclient API endpoints.
    - Intended for internal use within the Smarter platform to secure llmclient APIs.
    """

    class Meta:
        verbose_name_plural = "LLMClient API Keys"

    #: The LLMClient instance associated with this API key.
    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE)

    #: The API key (SmarterAuthToken) associated with the LLMClient.
    api_key = models.ForeignKey(SmarterAuthToken, on_delete=models.CASCADE)

    @classmethod
    def has_active_api_key(cls, llmclient: LLMClient, invalidate: Optional[bool] = False) -> bool:
        """Returns True if the llmclient has at least one active API key."""
        logger_prefix = logging.formatted_text(__name__ + "." + cls.__name__ + ".has_active_api_key()")

        @cache_results(cls.cache_expiration)
        def _has_active_api_key(llmclient_id: int, class_name: str) -> bool:
            logger.debug("%s querying and caching results for llmclient=%s", logger_prefix, llmclient)
            return cls.objects.filter(llmclient_id=llmclient_id, api_key__is_active=True).exists()

        if invalidate and llmclient:
            _has_active_api_key.invalidate(llmclient_id=llmclient.id, class_name=LLMClientAPIKey.__name__)  # type: ignore[union-attr]

        if llmclient:
            return _has_active_api_key(llmclient_id=llmclient.id, class_name=LLMClientAPIKey.__name__)  # type: ignore[return-value]
        return False

    # pylint: disable=W0221
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, llmclient: Optional[LLMClient] = None
    ) -> models.QuerySet["LLMClientAPIKey"]:
        """
        Retrieve a list of LLMClientAPIKey instances associated with a LLMClient using caching.

        Example usage:

        .. code-block:: python

            # Retrieve API keys for an llmclient with caching
            api_keys = LLMClientAPIKey.get_cached_objects(my_llmclient, invalidate=True)

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param llmclient: The LLMClient instance for which to retrieve API keys.
        :type llmclient: LLMClient, optional

        :returns: A queryset of LLMClientAPIKey instances associated with the LLMClient.
        :rtype: models.QuerySet["LLMClientAPIKey"]
        """
        logger_prefix = logging.formatted_text(__name__ + "." + LLMClientAPIKey.__name__ + ".get_cached_objects()")

        @cache_results(cls.cache_expiration)
        def _get_api_keys_for_llmclient_id(
            llmclient_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["LLMClientAPIKey"]:
            logger.debug("%s querying and caching results for llmclient=%s, ", logger_prefix, llmclient)
            return cls.objects.filter(llmclient_id=llmclient_id).select_related(
                "llmclient",
                "llmclient__user_profile",
                "llmclient__user_profile__user",
                "llmclient__user_profile__account",
                "api_key",
                "api_key__user_profile",
                "api_key__user_profile",
                "api_key__user_profile__user",
                "api_key__user_profile__account",
            )

        if invalidate and llmclient:
            _get_api_keys_for_llmclient_id.invalidate(llmclient_id=llmclient.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if llmclient:
            if LLMClientAPIKey.has_active_api_key(llmclient=llmclient, invalidate=invalidate):
                return _get_api_keys_for_llmclient_id(llmclient_id=llmclient.id, class_name=cls.__name__)  # type: ignore[return-value]
            return LLMClientAPIKey.objects.none()

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]


__all__ = [
    "LLMClientAPIKey",
]
