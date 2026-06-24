"""PluginDataStatic model for storing static plugin data configuration."""

from functools import lru_cache
from typing import Any, Optional, Union

from django.db import models

from smarter.apps.account.models.budget import charge_authorization
from smarter.common.conf import smarter_settings
from smarter.common.exceptions import SmarterValueError
from smarter.common.helpers.logger_helpers import formatted_text
from smarter.lib import json, logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import (
    dict_keys_to_list,
    list_of_dicts_to_dict,
    list_of_dicts_to_list,
)
from smarter.lib.django.waffle import SmarterWaffleSwitches

from .plugin_data_base import PluginDataBase
from .plugin_meta import PluginMeta

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.PLUGIN_LOGGING])
logger_prefix = formatted_text(f"{__name__}")


class PluginDataStatic(PluginDataBase):
    """
    Stores the configuration and static data set for a Smarter plugin.

    which is based on static data.

    This model is used for plugins that return static (predefined) data to the LLM.
    The ``static_data`` field holds the JSON data that will be returned when the plugin is invoked.
    This enables plugins to provide consistent, deterministic responses without external dependencies.

    ``PluginDataStatic`` provides methods for:
      - Returning sanitized static data, either as a dictionary or a list, with optional truncation for large datasets.
      - Extracting and caching all keys present in the static data, supporting both flat and nested structures.
      - Ensuring that the static data conforms to the expected structure and is compatible with the plugin's parameter schema.

    This model is a concrete subclass of :class:`PluginDataBase`, and is referenced by :class:`PluginMeta`
    to provide the data payload for static-type plugins. It is also used in conjunction with
    :class:`PluginSelector` and :class:`PluginPrompt` to enable full plugin lifecycle management.

    Typical use cases include plugins that serve reference data, lookup tables, or any information
    that does not require dynamic computation or remote queries.

    See also:

    - :class:`PluginDataBase`
    - :class:`PluginMeta`
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name = "Plugin Static Data"
        verbose_name_plural = "Plugin Static Data"

    static_data = models.JSONField(
        help_text="The JSON data that this plugin returns to OpenAI API when invoked by the user prompt.",
        default=dict,
        encoder=json.SmarterJSONEncoder,
    )
    """The JSON data that this plugin returns to OpenAI API when invoked by the user prompt."""

    def sanitized_return_data(self, params: Optional[dict] = None) -> Optional[Union[dict, list]]:
        """
        Return the static data for this plugin, either as a dictionary or a list.

        This method returns the value of ``self.static_data`` in a sanitized form:

        - If ``static_data`` is a dictionary, it is returned as-is.
        - If ``static_data`` is a list, it is truncated to ``smarter_settings.plugin_max_data_results`` items (if necessary)
          and converted to a dictionary using :func:`list_of_dicts_to_dict`.
        - If ``static_data`` is neither a dictionary nor a list, a :class:`SmarterValueError` is raised.

        :param params: Optional parameters for future extensibility (currently unused).
        :type params: Optional[dict]
        :return: The sanitized static data as a dictionary or list.
        :rtype: Optional[Union[dict, list]]
        :raises SmarterValueError: If ``static_data`` is not a dict or list.
        """
        retval: Union[dict, list, None] = None
        if isinstance(self.static_data, dict):
            return self.static_data
        if isinstance(self.static_data, list):
            retval = self.static_data
            if isinstance(retval, list) and len(retval) > 0:
                if len(retval) > smarter_settings.plugin_max_data_results:
                    logger.warning(
                        "%s.sanitized_return_data: Truncating static_data to %s items.",
                        self.formatted_class_name,
                        {smarter_settings.plugin_max_data_results},
                    )
                retval = retval[: smarter_settings.plugin_max_data_results]  # pylint: disable=E1136
                retval = list_of_dicts_to_dict(data=retval)
        else:
            raise SmarterValueError("static_data must be a dict or a list or None")

        return retval

    @property
    @lru_cache(maxsize=128)
    def return_data_keys(self) -> Optional[list[str]]:
        """
        Return all keys present in the ``static_data`` attribute.

        This property extracts, caches and returns a list of all keys found in the ``static_data`` field, supporting both dictionary and list formats:

        - If ``static_data`` is a dictionary, all nested keys are recursively collected and returned as a flat list.
        - If ``static_data`` is a list of dictionaries, the keys are extracted from each dictionary and returned as a list, truncated to ``smarter_settings.plugin_max_data_results`` items if necessary.
        - If ``static_data`` is neither a dictionary nor a list, a :class:`SmarterValueError` is raised.

        :return: A list of all keys in the static data, or None if not applicable.
        :rtype: Optional[list[str]]
        :raises SmarterValueError: If ``static_data`` is not a dict or list.

        **Example:**

        .. code-block:: python

            # If static_data is a dict:
            static_data = {"a": 1, "b": {"c": 2}}
            return_data_keys  # ['a', 'b', 'c']

            # If static_data is a list of dicts:
            static_data = [{"name": "Alice"}, {"name": "Bob"}]
            return_data_keys  # ['Alice', 'Bob']
        """

        retval: Optional[list[Any]] = []
        if isinstance(self.static_data, dict):
            retval = dict_keys_to_list(data=self.static_data)
            retval = list(retval) if retval else None
        elif isinstance(self.static_data, list):
            retval = self.static_data
            if isinstance(retval, list) and len(retval) > 0:
                if len(retval) > smarter_settings.plugin_max_data_results:
                    logger.warning(
                        "%s.return_data_keys: Truncating static_data to %s items.",
                        self.formatted_class_name,
                        {smarter_settings.plugin_max_data_results},
                    )
                retval = retval[: smarter_settings.plugin_max_data_results]  # pylint: disable=E1136
                retval = list_of_dicts_to_list(data=retval)
        else:
            raise SmarterValueError("static_data must be a dict or a list or None")

        return retval[: smarter_settings.plugin_max_data_results] if isinstance(retval, list) else retval

    def data(self, params: Optional[dict] = None) -> Optional[dict]:
        """
        Return the static data as a dictionary.

        This method attempts to parse and return the ``static_data`` field as a dictionary.

        :param params: Optional parameters for future extensibility (currently unused).
        :type params: Optional[dict]
        :return: The static data as a dictionary, or None if parsing fails.
        :rtype: Optional[dict]
        """
        try:
            data = json.loads(self.static_data)
            if not isinstance(data, dict):
                logger.warning("%s.data: static_data is not a dict, returning None.", self.formatted_class_name)
                return None
            return data
        except (json.JSONDecodeError, TypeError) as e:
            logger.error("%s.data: Failed to decode static_data JSON: %s", self.formatted_class_name, e)
            return None

    @classmethod
    def get_cached_data_by_plugin(cls, plugin: PluginMeta, invalidate: bool = False) -> Union["PluginDataStatic", None]:
        """
        Return a single instance of PluginDataStatic by plugin.

        This method caches the results to improve performance.

        :param plugin: The plugin whose data should be retrieved.
        :type plugin: PluginMeta
        :return: A PluginDataStatic instance if found, otherwise None.
        :rtype: Union[PluginDataStatic, None]
        """

        @cache_results()
        def data_by_plugin_id(plugin_id: int) -> Union["PluginDataStatic", None]:
            try:
                retval = cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
                logger.debug(
                    "%s.get_cached_data_by_plugin() fetched and cached PluginDataStatic for plugin_id: %s",
                    formatted_text(cls.__name__),
                    plugin_id,
                )
                return retval
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    formatted_text(cls.__name__),
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataStatic with plugin_id {plugin_id} does not exist.") from e

        if invalidate:
            data_by_plugin_id.invalidate(plugin.id)  # type: ignore[union-attr]

        return data_by_plugin_id(plugin.id)  # type: ignore[return-value]

    # pylint: disable=W0221
    @classmethod
    def get_cached_object(
        cls,
        *args,
        invalidate: Optional[bool] = False,
        pk: Optional[int] = None,
        plugin: Optional[PluginMeta] = None,
        **kwargs,
    ) -> Optional["PluginDataBase"]:
        """
        Retrieve a model instance by primary key, using caching to.

        optimize performance. This method is selectively overridden in
        models that inherit from MetaDataModel to provide class-specific
        function parameters.

        Example usage:

        .. code-block:: python

            # Retrieve by primary key
            instance = MyModel.get_cached_object(pk=1)

        :param invalidate: If True, invalidate the cache for this query before retrieving the object.
        :type invalidate: bool
        :param pk: The primary key of the model instance to retrieve.
        :type pk: int
        :param plugin: The PluginMeta instance associated with the data to retrieve.
        :type plugin: PluginMeta

        :returns: The model instance if found, otherwise None.
        :rtype: Optional["PluginDataBase"]
        """
        # pylint: disable=W0621
        logger_prefix = formatted_text(f"{__name__}.{PluginDataStatic.__name__}.get_cached_object()")
        logger.debug(
            "%s called with pk: %s, plugin: %s",
            logger_prefix,
            pk,
            plugin,
        )

        @cache_results()
        def _get_model_by_plugin_meta(plugin_id: int) -> Optional["PluginDataBase"]:
            try:
                logger.debug(
                    "%s._get_model_by_plugin_meta() cache miss for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                retval = cls.objects.prefetch_related("plugin").get(plugin_id=plugin_id)
                logger.debug(
                    "%s._get_model_by_plugin_meta() fetched and cached PluginDataStatic for plugin_id: %s",
                    logger_prefix,
                    plugin_id,
                )
                return retval
            except cls.DoesNotExist as e:
                logger.warning(
                    "%s.get_cached_data_by_plugin() - Data not found for plugin_id: %s",
                    cls.formatted_class_name,
                    plugin_id,
                )
                raise cls.DoesNotExist(f"PluginDataStatic with plugin_id {plugin_id} does not exist.") from e

        if invalidate and plugin:
            _get_model_by_plugin_meta.invalidate(plugin.id)  # type: ignore[union-attr]

        retval: "PluginDataStatic"
        if pk:
            retval = super().get_cached_object(*args, invalidate=invalidate, pk=pk, **kwargs)  # type: ignore[return-value]
            charge_authorization(retval.record_locator, cls.__name__)

        if plugin:
            retval = _get_model_by_plugin_meta(plugin.id)  # type: ignore[return-value]
            charge_authorization(retval.record_locator, cls.__name__)

        return retval
