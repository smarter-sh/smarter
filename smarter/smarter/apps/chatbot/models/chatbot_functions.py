"""All models for the OpenAI Function Calling API app."""

from typing import List, Optional

from django.db import models

from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .chatbot import ChatBot

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


class ChatBotFunctions(TimestampedModel):
    """
    Represents the set of callable functions that are available to a ChatBot instance within the Smarter platform.

    This model is used to define and manage the specific functions that a chatbot can access or invoke during its operation.
    Each record in this model links a chatbot to a named function, enabling fine-grained control over the chatbot's capabilities.
    The available functions are defined by a fixed set of choices, such as "weather", "news", "prices", and "math".

    By associating functions with chatbots, the platform allows for extensible and customizable chatbot behavior, supporting
    use cases where different chatbots require access to different sets of features or integrations. This model is essential
    for scenarios where chatbots need to perform actions, retrieve information, or interact with external APIs in a controlled
    and auditable manner.

    **Model Relationships**

    - Each ChatBotFunctions entry is linked to one :class:`ChatBot` instance.
    - Each entry specifies a function name from a predefined set of choices.

    **Usage Example**

    .. code-block:: python

        # Assign a function to a chatbot
        ChatBotFunctions.objects.create(chatbot=my_chatbot, name="weather")

        # List all functions available to a chatbot
        functions = ChatBotFunctions.objects.filter(chatbot=my_chatbot)

    **Notes**

    - The set of available functions is controlled by the ``CHOICES`` class attribute.
    - This model is intended for internal use to manage and audit chatbot capabilities.
    - Uniqueness is not enforced, so a chatbot may have multiple entries for the same function if needed.
    """

    class Meta:
        verbose_name_plural = "ChatBot Functions"

    CHOICES = [
        ("get_current_weather", "get_current_weather"),
        ("date_calculator", "date_calculator"),
        ("calculator", "calculator"),
    ]
    """
    The set of available function names that can be assigned to a ChatBot.

    See Also:

    - :func:`smarter.apps.prompt.functions.function_weather.get_current_weather`
    - :func:`smarter.apps.prompt.functions.function_date_calculator.date_calculator`
    - :func:`smarter.apps.prompt.functions.function_calculator.calculator`
    """

    #: The ChatBot instance associated with this function.
    #: Example: ChatBot(id=1, name="my-chatbot")
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)

    #: The name of the function available to the ChatBot.
    #: Example: "weather"
    name = models.CharField(max_length=255, choices=CHOICES, blank=True, null=True)

    @classmethod
    def choices_list(cls):
        return [item[0] for item in cls.CHOICES]

    @classmethod
    def functions(cls, chatbot: ChatBot) -> List[str]:
        """
        Returns a list of function names associated with the given ChatBot.

        :param chatbot: The ChatBot instance to retrieve functions for.
        :returns: List of function names.
        :rtype: List[str]
        """
        if not chatbot:
            return []
        chatbot_functions = cls.objects.filter(chatbot=chatbot)
        retval = [chatbot_function.name for chatbot_function in chatbot_functions if chatbot_function.name]
        return retval

    # pylint: disable=W0221
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, chatbot: Optional[ChatBot] = None
    ) -> models.QuerySet["ChatBotFunctions"]:
        """
        Retrieve a queryset of ChatBotFunctions instances associated with a ChatBot using caching.

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param chatbot: The ChatBot instance for which to retrieve functions.
        :type chatbot: ChatBot, optional

                :returns: A queryset of ChatBotFunctions instances associated with the ChatBot.
        :rtype: models.QuerySet["ChatBotFunctions"]

        """
        logger_prefix = logging.formatted_text(__name__ + "." + ChatBotFunctions.__name__ + ".get_cached_objects()")
        logger.debug("%s called with chatbot=%s, invalidate=%s", logger_prefix, chatbot, invalidate)

        @cache_results(cls.cache_expiration)
        def _get_functions_for_chatbot_id(
            chatbot_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["ChatBotFunctions"]:
            """
            Caches the functions for a chatbot by chatbot_id to optimize
            performance and reduce database queries.

            :param chatbot_id: The ID of the ChatBot for which to retrieve functions.
            :param class_name: The name of the class for cache key purposes.
            :returns: A queryset of ChatBotFunctions instances associated with the ChatBot.
            :rtype: models.QuerySet["ChatBotFunctions"]
            """
            return cls.objects.filter(chatbot_id=chatbot_id).select_related(
                "plugin_meta",
                "plugin_meta__user_profile",
                "plugin_meta__user_profile__user",
                "plugin_meta__user_profile__account",
                "chatbot__user_profile",
                "chatbot__user_profile__user",
                "chatbot__user_profile__account",
            )

        if invalidate and chatbot:
            _get_functions_for_chatbot_id.invalidate(chatbot_id=chatbot.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if chatbot:
            return _get_functions_for_chatbot_id(chatbot_id=chatbot.id, class_name=cls.__name__)  # type: ignore[return-value]

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]


__all__ = [
    "ChatBotFunctions",
]
