"""All models for the OpenAI Function Calling API app."""

from typing import List, Optional

from django.db import models

from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .llm_client import LLMClient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


class LLMClientFunctions(TimestampedModel):
    """
    Represents the set of callable functions that are available to a LLMClient instance within the Smarter platform.

    This model is used to define and manage the specific functions that a llm_client can access or invoke during its operation.
    Each record in this model links a llm_client to a named function, enabling fine-grained control over the llm_client's capabilities.
    The available functions are defined by a fixed set of choices, such as "weather", "news", "prices", and "math".

    By associating functions with llm_clients, the platform allows for extensible and customizable llm_client behavior, supporting
    use cases where different llm_clients require access to different sets of features or integrations. This model is essential
    for scenarios where llm_clients need to perform actions, retrieve information, or interact with external APIs in a controlled
    and auditable manner.

    **Model Relationships**

    - Each LLMClientFunctions entry is linked to one :class:`LLMClient` instance.
    - Each entry specifies a function name from a predefined set of choices.

    **Usage Example**

    .. code-block:: python

        # Assign a function to a llm_client
        LLMClientFunctions.objects.create(llm_client=my_llm_client, name="weather")

        # List all functions available to a llm_client
        functions = LLMClientFunctions.objects.filter(llm_client=my_llm_client)

    **Notes**

    - The set of available functions is controlled by the ``CHOICES`` class attribute.
    - This model is intended for internal use to manage and audit llm_client capabilities.
    - Uniqueness is not enforced, so a llm_client may have multiple entries for the same function if needed.
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
    #: Example: LLMClient(id=1, name="my-llm_client")
    llm_client = models.ForeignKey(LLMClient, on_delete=models.CASCADE)

    #: The name of the function available to the LLMClient.
    #: Example: "weather"
    name = models.CharField(max_length=255, choices=CHOICES, blank=True, null=True)

    @classmethod
    def choices_list(cls):
        return [item[0] for item in cls.CHOICES]

    @classmethod
    def functions(cls, llm_client: LLMClient) -> List[str]:
        """
        Returns a list of function names associated with the given LLMClient.

        :param llm_client: The LLMClient instance to retrieve functions for.
        :returns: List of function names.
        :rtype: List[str]
        """
        if not llm_client:
            return []
        llm_client_functions = cls.objects.filter(llm_client=llm_client)
        retval = [llm_client_function.name for llm_client_function in llm_client_functions if llm_client_function.name]
        return retval

    # pylint: disable=W0221
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, llm_client: Optional[LLMClient] = None
    ) -> models.QuerySet["LLMClientFunctions"]:
        """
        Retrieve a queryset of LLMClientFunctions instances associated with a LLMClient using caching.

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param llm_client: The LLMClient instance for which to retrieve functions.
        :type llm_client: LLMClient, optional

                :returns: A queryset of LLMClientFunctions instances associated with the LLMClient.
        :rtype: models.QuerySet["LLMClientFunctions"]
        """
        logger_prefix = logging.formatted_text(__name__ + "." + LLMClientFunctions.__name__ + ".get_cached_objects()")

        @cache_results(cls.cache_expiration)
        def _get_functions_for_llm_client_id(
            llm_client_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["LLMClientFunctions"]:
            """
            Caches the functions for a llm_client by llm_client_id to optimize.

            performance and reduce database queries.

            :param llm_client_id: The ID of the LLMClient for which to retrieve functions.
            :param class_name: The name of the class for cache key purposes.
            :returns: A queryset of LLMClientFunctions instances associated with the LLMClient.
            :rtype: models.QuerySet["LLMClientFunctions"]
            """
            logger.debug("%s called with llm_client=%s, invalidate=%s", logger_prefix, llm_client, invalidate)
            retval = cls.objects.filter(llm_client_id=llm_client_id).select_related(
                "plugin_meta",
                "plugin_meta__user_profile",
                "plugin_meta__user_profile__user",
                "plugin_meta__user_profile__account",
                "llm_client__user_profile",
                "llm_client__user_profile__user",
                "llm_client__user_profile__account",
            )
            logger.debug(
                "%s._get_functions_for_llm_client_id() fetched and cached %s functions for llm_client_id: %s",
                logger_prefix,
                len(retval),
                llm_client_id,
            )
            return retval

        if invalidate and llm_client:
            _get_functions_for_llm_client_id.invalidate(llm_client_id=llm_client.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if llm_client:
            return _get_functions_for_llm_client_id(llm_client_id=llm_client.id, class_name=cls.__name__)  # type: ignore[return-value]

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]


__all__ = [
    "LLMClientFunctions",
]
