"""All models for the OpenAI Function Calling API app."""

from typing import List, Optional

from django.db import models

from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .llmclient import LLMClient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


class LLMClientFunctions(TimestampedModel):
    """
    Represents the set of callable functions that are available to a LLMClient instance within the Smarter platform.

    This model is used to define and manage the specific functions that an llmclient can access or invoke during its operation.
    Each record in this model links an llmclient to a named function, enabling fine-grained control over the llmclient's capabilities.
    The available functions are defined by a fixed set of choices, such as "weather", "news", "prices", and "math".

    By associating functions with llmclients, the platform allows for extensible and customizable llmclient behavior, supporting
    use cases where different llmclients require access to different sets of features or integrations. This model is essential
    for scenarios where llmclients need to perform actions, retrieve information, or interact with external APIs in a controlled
    and auditable manner.

    **Model Relationships**

    - Each LLMClientFunctions entry is linked to one :class:`LLMClient` instance.
    - Each entry specifies a function name from a predefined set of choices.

    **Usage Example**

    .. code-block:: python

        # Assign a function to an llmclient
        LLMClientFunctions.objects.create(llmclient=my_llmclient, name="weather")

        # List all functions available to an llmclient
        functions = LLMClientFunctions.objects.filter(llmclient=my_llmclient)

    **Notes**

    - The set of available functions is controlled by the ``CHOICES`` class attribute.
    - This model is intended for internal use to manage and audit llmclient capabilities.
    - Uniqueness is not enforced, so an llmclient may have multiple entries for the same function if needed.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMClient Functions"

    CHOICES = [
        ("get_current_weather", "get_current_weather"),
        ("date_calculator", "date_calculator"),
        ("calculator", "calculator"),
    ]
    """
    The set of available function names that can be assigned to a LLMClient.

    See Also:

    - :func:`smarter.apps.prompt.functions.function_weather.get_current_weather`
    - :func:`smarter.apps.prompt.functions.function_date_calculator.date_calculator`
    - :func:`smarter.apps.prompt.functions.function_calculator.calculator`
    """

    #: The LLMClient instance associated with this function.
    #: Example: LLMClient(id=1, name="my-llmclient")
    llmclient = models.ForeignKey(LLMClient, on_delete=models.CASCADE)

    #: The name of the function available to the LLMClient.
    #: Example: "weather"
    name = models.CharField(max_length=255, choices=CHOICES, blank=True, null=True)

    @classmethod
    def choices_list(cls):
        return [item[0] for item in cls.CHOICES]

    @classmethod
    def functions(cls, llmclient: LLMClient) -> List[str]:
        """
        Returns a list of function names associated with the given LLMClient.

        :param llmclient: The LLMClient instance to retrieve functions for.
        :returns: List of function names.
        :rtype: List[str]
        """
        if not llmclient:
            return []
        llmclient_functions = cls.objects.filter(llmclient=llmclient)
        retval = [llmclient_function.name for llmclient_function in llmclient_functions if llmclient_function.name]
        return retval

    # pylint: disable=W0221
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, llmclient: Optional[LLMClient] = None
    ) -> models.QuerySet["LLMClientFunctions"]:
        """
        Retrieve a queryset of LLMClientFunctions instances associated with a LLMClient using caching.

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param llmclient: The LLMClient instance for which to retrieve functions.
        :type llmclient: LLMClient, optional

                :returns: A queryset of LLMClientFunctions instances associated with the LLMClient.
        :rtype: models.QuerySet["LLMClientFunctions"]
        """
        logger_prefix = logging.formatted_text(__name__ + "." + LLMClientFunctions.__name__ + ".get_cached_objects()")

        @cache_results(cls.cache_expiration)
        def _get_functions_for_llmclient_id(
            llmclient_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["LLMClientFunctions"]:
            """
            Caches the functions for an llmclient by llmclient_id to optimize.

            performance and reduce database queries.

            :param llmclient_id: The ID of the LLMClient for which to retrieve functions.
            :param class_name: The name of the class for cache key purposes.
            :returns: A queryset of LLMClientFunctions instances associated with the LLMClient.
            :rtype: models.QuerySet["LLMClientFunctions"]
            """
            logger.debug("%s called with llmclient=%s, invalidate=%s", logger_prefix, llmclient, invalidate)
            retval = cls.objects.filter(llmclient_id=llmclient_id).select_related(
                "plugin_meta",
                "plugin_meta__user_profile",
                "plugin_meta__user_profile__user",
                "plugin_meta__user_profile__account",
                "llmclient__user_profile",
                "llmclient__user_profile__user",
                "llmclient__user_profile__account",
            )
            logger.debug(
                "%s._get_functions_for_llmclient_id() fetched and cached %s functions for llmclient_id: %s",
                logger_prefix,
                len(retval),
                llmclient_id,
            )
            return retval

        if invalidate and llmclient:
            _get_functions_for_llmclient_id.invalidate(llmclient_id=llmclient.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if llmclient:
            return _get_functions_for_llmclient_id(llmclient_id=llmclient.id, class_name=cls.__name__)  # type: ignore[return-value]

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]


__all__ = [
    "LLMClientFunctions",
]
