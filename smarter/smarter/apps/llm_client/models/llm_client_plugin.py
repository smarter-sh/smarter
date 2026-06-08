"""All models for the OpenAI Function Calling API app."""

from typing import List, Optional, Type

from django.db import models

from smarter.apps.account.models import (
    UserProfile,
)
from smarter.apps.plugin.manifest.controller import PluginController
from smarter.apps.plugin.manifest.models.common.plugin.model import SAMPluginCommon
from smarter.apps.plugin.models import PluginMeta
from smarter.apps.plugin.plugin.base import PluginBase
from smarter.common.exceptions import SmarterValueError
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.loader import SAMLoader

from .llm_client import LLMClient

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.LLM_CLIENT_LOGGING])


class LLMClientPlugin(TimestampedModel):
    """
    Represents the association between a LLMClient instance and its enabled plugins within the Smarter platform.

    This model establishes a many-to-one relationship, where each plugin entry is linked to a specific LLMClient
    and references metadata describing the plugin. By maintaining this mapping, the platform can manage which
    plugins are available to each llm_client, enabling extensibility and customization of llm_client capabilities.

    The LLMClientPlugin model supports use cases such as plugin activation, deactivation, and enumeration for
    individual llm_clients. It is essential for scenarios where llm_clients require additional functionality
    provided by external or internal plugins, such as integrations, enhanced processing, or custom behaviors.

    **Model Relationships**

    - Each LLMClientPlugin is linked to one :class:`LLMClient` instance.
    - Each LLMClientPlugin references one :class:`PluginMeta` instance, which contains metadata about the plugin.

    **Usage Example**

    .. code-block:: python

        # Add a plugin to a llm_client
        plugin_meta = PluginMeta.objects.get(name="weather")
        llm_client_plugin = LLMClientPlugin.objects.create(llm_client=my_llm_client, plugin_meta=plugin_meta)

        # List all plugins for a llm_client
        plugins = LLMClientPlugin.objects.filter(llm_client=my_llm_client)

    **Notes**

    - Plugin management and loading are handled via the PluginController and related infrastructure.
    - This model is intended for internal use to support dynamic extension of llm_client features.
    - Uniqueness is enforced for each (llm_client, plugin_meta) pair to prevent duplicate plugin assignments.
    """

    # pylint: disable=C0115
    class Meta:
        verbose_name_plural = "LLMClient Plugins"
        unique_together = ("llm_client", "plugin_meta")

    #: The LLMClient instance associated with this plugin.
    llm_client = models.ForeignKey(LLMClient, on_delete=models.CASCADE)

    #: The metadata for the plugin associated with the LLMClient.
    plugin_meta = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)

    def __str__(self):
        try:
            url = self.llm_client.url if self.llm_client else "undefined llm_client"
            plugin_name = self.plugin_meta.name if self.plugin_meta else "undefined plugin"
        except LLMClient.DoesNotExist:
            url = "undefined llm_client"
        except PluginMeta.DoesNotExist:
            plugin_name = "undefined plugin"
        return f"{url} - {plugin_name}"

    @property
    def plugin(self) -> Optional[PluginBase]:
        """
        Returns the Plugin instance associated with this LLMClientPlugin.

        :returns: Plugin instance or None
        :rtype: Optional[PluginBase]
        """
        if not self.llm_client:
            return None
        admin_user = UserProfile.admin_for_account(self.llm_client.user_profile.cached_account)
        if admin_user is None:
            raise SmarterValueError("LLMClientPlugin.plugin() failed to find admin user for llm_client account")
        user_profile = UserProfile.get_cached_object(invalidate=False, user=admin_user)

        @cache_results()
        def get_cached_plugin_controller(
            account_id: int,
            user_id: int,
            plugin_meta_id: int,
            user_profile_id: int,
            class_name: str = self.__class__.__name__,
        ) -> PluginController:

            retval = PluginController(
                account=self.llm_client.user_profile.cached_account,
                user=admin_user,
                plugin_meta=self.plugin_meta,
                user_profile=user_profile,
            )
            logger.debug(
                "%s.get_cached_plugin_controller() fetched and cached plugin controller for llm_client_id: %s, plugin_meta_id: %s",
                class_name,
                self.llm_client.id,
                self.plugin_meta.id,
            )
            return retval

        plugin_controller = get_cached_plugin_controller(
            account_id=self.llm_client.user_profile.cached_account.id,
            user_id=admin_user.id,  # type: ignore[union-attr]
            plugin_meta_id=self.plugin_meta.id,
            user_profile_id=user_profile.id,  # type: ignore[union-attr]
            class_name=self.__class__.__name__,
        )
        this_plugin = plugin_controller.plugin
        return this_plugin

    @classmethod
    def load(cls: Type["LLMClientPlugin"], llm_client: LLMClient, data) -> "LLMClientPlugin":
        """
        Load (aka import) a plugin from a data file in yaml or json format.

        :param llm_client: The LLMClient instance to associate with the plugin.
        :param data: The plugin manifest data in yaml or json format.
        :returns: The created LLMClientPlugin instance.
        :rtype: LLMClientPlugin

        See Also:

        - :py:class:`smarter.apps.plugin.manifest.controller.PluginController`
        - :py:class:`smarter.lib.manifest.loader.SAMLoader`
        """
        if not llm_client:
            return None
        admin_user = UserProfile.admin_for_account(llm_client.user_profile.cached_account)
        if admin_user is None:
            raise SmarterValueError("LLMClientPlugin.plugin() failed to find admin user for llm_client account")
        user_profile = UserProfile.get_cached_object(invalidate=False, user=admin_user)
        loader = SAMLoader(manifest=data)
        manifest = SAMPluginCommon(**loader.json_data)  # type: ignore[call-arg]
        plugin_controller = PluginController(user_profile=user_profile, manifest=manifest)
        plugin = plugin_controller.plugin
        if not plugin or plugin.plugin_meta is None:
            raise SmarterValueError("LLMClientPlugin.load() failed to load plugin from data file")
        return cls.objects.create(llm_client=llm_client, plugin_meta=plugin.plugin_meta)

    @classmethod
    def plugins(cls, llm_client: LLMClient) -> List[PluginBase]:
        """
        Returns a list of Plugin instances associated with the given LLMClient.

        :param llm_client: The LLMClient instance to retrieve plugins for.
        :returns: List of Plugin instances.
        :rtype: List[PluginBase]

        :raises SmarterValueError: If admin user for llm_client account is not found
                                   or if a plugin fails to load.

        See Also:

        - :py:class:`smarter.apps.plugin.controller.PluginController`
        """
        if not llm_client:
            return []
        llm_client_plugins = cls.objects.filter(llm_client=llm_client)
        admin_user = UserProfile.admin_for_account(llm_client.user_profile.cached_account)
        if admin_user is None:
            raise SmarterValueError("LLMClientPlugin.plugin() failed to find admin user for llm_client account")
        user_profile = UserProfile.get_cached_object(invalidate=False, user=admin_user)
        retval = []
        for llm_client_plugin in llm_client_plugins:
            plugin_controller = PluginController(
                user_profile=user_profile,
                plugin_meta=llm_client_plugin.plugin_meta,
            )
            if not plugin_controller or not plugin_controller.plugin:
                raise SmarterValueError(
                    f"LLMClientPlugin.plugins() failed to load plugin for {llm_client_plugin.plugin_meta.name}"
                )
            retval.append(plugin_controller.plugin)
        return retval

    # pylint: disable=W0221
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, llm_client: Optional[LLMClient] = None
    ) -> models.QuerySet["LLMClientPlugin"]:
        """
        Retrieve a queryset of LLMClientPlugin instances associated with a LLMClient using caching.

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param llm_client: The LLMClient instance for which to retrieve plugins.
        :type llm_client: LLMClient, optional

        :returns: A queryset of LLMClientPlugin instances associated with the LLMClient.
        :rtype: models.QuerySet["LLMClientPlugin"]
        """
        logger_prefix = logging.formatted_text(__name__ + "." + LLMClientPlugin.__name__ + ".get_cached_objects()")

        @cache_results()
        def _get_plugins_for_llm_client_id(
            llm_client_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["LLMClientPlugin"]:
            """
            Caches the plugins for a llm_client by llm_client_id to optimize.

            performance and reduce database queries.

            :param llm_client_id: The ID of the LLMClient for which to retrieve plugins.
            :param class_name: The name of the class for cache key purposes.
            :returns: A queryset of LLMClientPlugin instances associated with the LLMClient.
            :rtype: models.QuerySet["LLMClientPlugin"]
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
                "%s._get_plugins_for_llm_client_id() fetched and cached %s plugins for llm_client_id: %s",
                logger_prefix,
                len(retval),
                llm_client_id,
            )
            return retval

        if invalidate and llm_client:
            _get_plugins_for_llm_client_id.invalidate(llm_client_id=llm_client.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if llm_client:
            return _get_plugins_for_llm_client_id(llm_client_id=llm_client.id, class_name=cls.__name__)  # type: ignore[return-value]

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]

    @classmethod
    def plugins_json(cls, llm_client: LLMClient) -> List[dict]:
        retval = []
        for plugin in cls.plugins(llm_client):
            retval.append(plugin.to_json())
        return retval


__all__ = [
    "LLMClientPlugin",
]
