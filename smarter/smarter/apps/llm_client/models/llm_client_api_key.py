"""LLMClientAPIKey model for managing API keys associated with LLMClient instances in the Smarter platform."""

from typing import Optional

from django.db import models

from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken

from .llm_client import LLMClient

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
    over which keys can interact with which llm_client instances.

    The LLMClientAPIKey model is essential for managing access to llm_client APIs, supporting
    use cases such as per-bot API key rotation, revocation, and auditing. By associating
    API keys with individual llm_clients, the platform can enforce security policies and
    monitor usage at the llm_client level.

    Typical usage involves creating a LLMClientAPIKey instance whenever a new API key is
    provisioned for a llm_client, and querying this model to validate incoming requests
    against active keys.

    **Model Relationships**

    - Each LLMClientAPIKey is linked to one :class:`LLMClient` instance.
    - Each LLMClientAPIKey references one :class:`SmarterAuthToken` representing the API key.

    **Example**

    .. code-block:: python

        # Assign an API key to a llm_client
        api_key = SmarterAuthToken.objects.create(...)
        llm_client_api_key = LLMClientAPIKey.objects.create(llm_client=my_llm_client, api_key=api_key)

        # Query API keys for a llm_client
        keys = LLMClientAPIKey.objects.filter(llm_client=my_llm_client)

    **Notes**

    - API key activation and deactivation are managed via the SmarterAuthToken model.
    - This model supports auditing and access control for llm_client API endpoints.
    - Intended for internal use within the Smarter platform to secure llm_client APIs.
    """

    class Meta:
        verbose_name_plural = "LLMClient API Keys"

    #: The LLMClient instance associated with this API key.
    llm_client = models.ForeignKey(LLMClient, on_delete=models.CASCADE)

    #: The API key (SmarterAuthToken) associated with the LLMClient.
    api_key = models.ForeignKey(SmarterAuthToken, on_delete=models.CASCADE)

    @classmethod
    def has_active_api_key(cls, llm_client: LLMClient, invalidate: Optional[bool] = False) -> bool:
        """Returns True if the llm_client has at least one active API key."""
        logger_prefix = logging.formatted_text(__name__ + "." + cls.__name__ + ".has_active_api_key()")

        @cache_results(cls.cache_expiration)
        def _has_active_api_key(llm_client_id: int, class_name: str) -> bool:
            logger.debug("%s querying and caching results for llm_client=%s", logger_prefix, llm_client)
            return cls.objects.filter(llm_client_id=llm_client_id, api_key__is_active=True).exists()

        if invalidate and llm_client:
            _has_active_api_key.invalidate(llm_client_id=llm_client.id, class_name=LLMClientAPIKey.__name__)  # type: ignore[union-attr]

        if llm_client:
            return _has_active_api_key(llm_client_id=llm_client.id, class_name=LLMClientAPIKey.__name__)  # type: ignore[return-value]
        return False

    # pylint: disable=W0221
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, llm_client: Optional[LLMClient] = None
    ) -> models.QuerySet["LLMClientAPIKey"]:
        """
        Retrieve a list of LLMClientAPIKey instances associated with a LLMClient using caching.

        Example usage:

        .. code-block:: python

            # Retrieve API keys for a llm_client with caching
            api_keys = LLMClientAPIKey.get_cached_objects(my_llm_client, invalidate=True)

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param llm_client: The LLMClient instance for which to retrieve API keys.
        :type llm_client: LLMClient, optional

        :returns: A queryset of LLMClientAPIKey instances associated with the LLMClient.
        :rtype: models.QuerySet["LLMClientAPIKey"]
        """
        logger_prefix = logging.formatted_text(__name__ + "." + LLMClientAPIKey.__name__ + ".get_cached_objects()")

        @cache_results(cls.cache_expiration)
        def _get_api_keys_for_llm_client_id(
            llm_client_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["LLMClientAPIKey"]:
            logger.debug("%s querying and caching results for llm_client=%s, ", logger_prefix, llm_client)
            return cls.objects.filter(llm_client_id=llm_client_id).select_related(
                "llm_client",
                "llm_client__user_profile",
                "llm_client__user_profile__user",
                "llm_client__user_profile__account",
                "api_key",
                "api_key__user_profile",
                "api_key__user_profile",
                "api_key__user_profile__user",
                "api_key__user_profile__account",
            )

        if invalidate and llm_client:
            _get_api_keys_for_llm_client_id.invalidate(llm_client_id=llm_client.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if llm_client:
            if LLMClientAPIKey.has_active_api_key(llm_client=llm_client, invalidate=invalidate):
                return _get_api_keys_for_llm_client_id(llm_client_id=llm_client.id, class_name=cls.__name__)  # type: ignore[return-value]
            return LLMClientAPIKey.objects.none()

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]


__all__ = [
    "LLMClientAPIKey",
]
