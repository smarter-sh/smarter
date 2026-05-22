"""
ChatBotAPIKey model for managing API keys associated with ChatBot instances in the Smarter platform.
"""

from typing import Optional

from django.db import models

from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.drf.models import SmarterAuthToken

from .chatbot import ChatBot

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


class ChatBotAPIKey(TimestampedModel):
    """
    Represents the mapping of API keys to ChatBot instances within the Smarter platform.

    .. important::

        If present, the ChatBot associated with this record will require Api Key authentication
        for all API requests. Otherwise, the ChatBot will allow anonymous unauthenticated access.

        See :class:`smarter.lib.drf.token_authentication.SmarterTokenAuthentication` .

    This model establishes a relationship between a ChatBot and its associated API keys,
    enabling secure authentication and authorization for API access. Each entry in this
    model links a specific ChatBot to a unique API key, allowing fine-grained control
    over which keys can interact with which chatbot instances.

    The ChatBotAPIKey model is essential for managing access to chatbot APIs, supporting
    use cases such as per-bot API key rotation, revocation, and auditing. By associating
    API keys with individual chatbots, the platform can enforce security policies and
    monitor usage at the chatbot level.

    Typical usage involves creating a ChatBotAPIKey instance whenever a new API key is
    provisioned for a chatbot, and querying this model to validate incoming requests
    against active keys.

    **Model Relationships**

    - Each ChatBotAPIKey is linked to one :class:`ChatBot` instance.
    - Each ChatBotAPIKey references one :class:`SmarterAuthToken` representing the API key.

    **Example**

    .. code-block:: python

        # Assign an API key to a chatbot
        api_key = SmarterAuthToken.objects.create(...)
        chatbot_api_key = ChatBotAPIKey.objects.create(chatbot=my_chatbot, api_key=api_key)

        # Query API keys for a chatbot
        keys = ChatBotAPIKey.objects.filter(chatbot=my_chatbot)

    **Notes**

    - API key activation and deactivation are managed via the SmarterAuthToken model.
    - This model supports auditing and access control for chatbot API endpoints.
    - Intended for internal use within the Smarter platform to secure chatbot APIs.
    """

    class Meta:
        verbose_name_plural = "ChatBot API Keys"

    #: The ChatBot instance associated with this API key.
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)

    #: The API key (SmarterAuthToken) associated with the ChatBot.
    api_key = models.ForeignKey(SmarterAuthToken, on_delete=models.CASCADE)

    @classmethod
    def has_active_api_key(cls, chatbot: ChatBot, invalidate: Optional[bool] = False) -> bool:
        """
        Returns True if the chatbot has at least one active API key.
        """
        logger_prefix = logging.formatted_text(__name__ + "." + cls.__name__ + ".has_active_api_key()")

        @cache_results(cls.cache_expiration)
        def _has_active_api_key(chatbot_id: int, class_name: str) -> bool:
            logger.debug("%s querying and caching results for chatbot=%s", logger_prefix, chatbot)
            return cls.objects.filter(chatbot_id=chatbot_id, api_key__is_active=True).exists()

        if invalidate and chatbot:
            _has_active_api_key.invalidate(chatbot_id=chatbot.id, class_name=ChatBotAPIKey.__name__)  # type: ignore[union-attr]

        if chatbot:
            return _has_active_api_key(chatbot_id=chatbot.id, class_name=ChatBotAPIKey.__name__)  # type: ignore[return-value]
        return False

    # pylint: disable=W0221
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, chatbot: Optional[ChatBot] = None
    ) -> models.QuerySet["ChatBotAPIKey"]:
        """
        Retrieve a list of ChatBotAPIKey instances associated with a ChatBot using caching.

        Example usage:

        .. code-block:: python

            # Retrieve API keys for a chatbot with caching
            api_keys = ChatBotAPIKey.get_cached_objects(my_chatbot, invalidate=True)

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param chatbot: The ChatBot instance for which to retrieve API keys.
        :type chatbot: ChatBot, optional

        :returns: A queryset of ChatBotAPIKey instances associated with the ChatBot.
        :rtype: models.QuerySet["ChatBotAPIKey"]

        """
        logger_prefix = logging.formatted_text(__name__ + "." + ChatBotAPIKey.__name__ + ".get_cached_objects()")

        @cache_results(cls.cache_expiration)
        def _get_api_keys_for_chatbot_id(
            chatbot_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["ChatBotAPIKey"]:
            logger.debug("%s querying and caching results for chatbot=%s, ", logger_prefix, chatbot)
            return cls.objects.filter(chatbot_id=chatbot_id).select_related(
                "chatbot",
                "chatbot__user_profile",
                "chatbot__user_profile__user",
                "chatbot__user_profile__account",
                "api_key",
                "api_key__user_profile",
                "api_key__user_profile",
                "api_key__user_profile__user",
                "api_key__user_profile__account",
            )

        if invalidate and chatbot:
            _get_api_keys_for_chatbot_id.invalidate(chatbot_id=chatbot.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if chatbot:
            if ChatBotAPIKey.has_active_api_key(chatbot=chatbot, invalidate=invalidate):
                return _get_api_keys_for_chatbot_id(chatbot_id=chatbot.id, class_name=cls.__name__)  # type: ignore[return-value]
            return ChatBotAPIKey.objects.none()

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]


__all__ = [
    "ChatBotAPIKey",
]
