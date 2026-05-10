# pylint: disable=W0613,C0115,C0302
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
from smarter.common.helpers.console_helpers import (
    formatted_text,
)
from smarter.lib import logging
from smarter.lib.cache import cache_results
from smarter.lib.django.models import TimestampedModel
from smarter.lib.django.waffle import SmarterWaffleSwitches
from smarter.lib.manifest.loader import SAMLoader

from .chatbot import ChatBot

logger = logging.getSmarterLogger(__name__, any_switches=[SmarterWaffleSwitches.CHATBOT_LOGGING])


class ChatBotPlugin(TimestampedModel):
    """
    Represents the association between a ChatBot instance and its enabled plugins within the Smarter platform.

    This model establishes a many-to-one relationship, where each plugin entry is linked to a specific ChatBot
    and references metadata describing the plugin. By maintaining this mapping, the platform can manage which
    plugins are available to each chatbot, enabling extensibility and customization of chatbot capabilities.

    The ChatBotPlugin model supports use cases such as plugin activation, deactivation, and enumeration for
    individual chatbots. It is essential for scenarios where chatbots require additional functionality
    provided by external or internal plugins, such as integrations, enhanced processing, or custom behaviors.

    **Model Relationships**

    - Each ChatBotPlugin is linked to one :class:`ChatBot` instance.
    - Each ChatBotPlugin references one :class:`PluginMeta` instance, which contains metadata about the plugin.

    **Usage Example**

    .. code-block:: python

        # Add a plugin to a chatbot
        plugin_meta = PluginMeta.objects.get(name="weather")
        chatbot_plugin = ChatBotPlugin.objects.create(chatbot=my_chatbot, plugin_meta=plugin_meta)

        # List all plugins for a chatbot
        plugins = ChatBotPlugin.objects.filter(chatbot=my_chatbot)

    **Notes**

    - Plugin management and loading are handled via the PluginController and related infrastructure.
    - This model is intended for internal use to support dynamic extension of chatbot features.
    - Uniqueness is enforced for each (chatbot, plugin_meta) pair to prevent duplicate plugin assignments.
    """

    class Meta:
        verbose_name_plural = "ChatBot Plugins"
        unique_together = ("chatbot", "plugin_meta")

    #: The ChatBot instance associated with this plugin.
    chatbot = models.ForeignKey(ChatBot, on_delete=models.CASCADE)

    #: The metadata for the plugin associated with the ChatBot.
    plugin_meta = models.ForeignKey(PluginMeta, on_delete=models.CASCADE)

    def __str__(self):
        try:
            url = self.chatbot.url if self.chatbot else "undefined chatbot"
            plugin_name = self.plugin_meta.name if self.plugin_meta else "undefined plugin"
        except ChatBot.DoesNotExist:
            url = "undefined chatbot"
        except PluginMeta.DoesNotExist:
            plugin_name = "undefined plugin"
        return f"{url} - {plugin_name}"

    @property
    def plugin(self) -> Optional[PluginBase]:
        """
        Returns the Plugin instance associated with this ChatBotPlugin.

        :returns: Plugin instance or None
        :rtype: Optional[PluginBase]
        """
        if not self.chatbot:
            return None
        admin_user = UserProfile.admin_for_account(self.chatbot.user_profile.cached_account)
        if admin_user is None:
            raise SmarterValueError("ChatBotPlugin.plugin() failed to find admin user for chatbot account")
        user_profile = UserProfile.get_cached_object(invalidate=False, user=admin_user)

        @cache_results()
        def get_cached_plugin_controller(
            account_id: int,
            user_id: int,
            plugin_meta_id: int,
            user_profile_id: int,
            class_name: str = self.__class__.__name__,
        ) -> PluginController:

            return PluginController(
                account=self.chatbot.user_profile.cached_account,
                user=admin_user,
                plugin_meta=self.plugin_meta,
                user_profile=user_profile,
            )

        plugin_controller = get_cached_plugin_controller(
            account_id=self.chatbot.user_profile.cached_account.id,
            user_id=admin_user.id,  # type: ignore[union-attr]
            plugin_meta_id=self.plugin_meta.id,
            user_profile_id=user_profile.id,  # type: ignore[union-attr]
            class_name=self.__class__.__name__,
        )
        this_plugin = plugin_controller.plugin
        return this_plugin

    @classmethod
    def load(cls: Type["ChatBotPlugin"], chatbot: ChatBot, data) -> "ChatBotPlugin":
        """
        Load (aka import) a plugin from a data file in yaml or json format.

        :param chatbot: The ChatBot instance to associate with the plugin.
        :param data: The plugin manifest data in yaml or json format.
        :returns: The created ChatBotPlugin instance.
        :rtype: ChatBotPlugin

        See Also:

        - :py:class:`smarter.apps.plugin.manifest.controller.PluginController`
        - :py:class:`smarter.lib.manifest.loader.SAMLoader`
        """
        if not chatbot:
            return None
        admin_user = UserProfile.admin_for_account(chatbot.user_profile.cached_account)
        if admin_user is None:
            raise SmarterValueError("ChatBotPlugin.plugin() failed to find admin user for chatbot account")
        user_profile = UserProfile.get_cached_object(invalidate=False, user=admin_user)
        loader = SAMLoader(manifest=data)
        manifest = SAMPluginCommon(**loader.json_data)  # type: ignore[call-arg]
        plugin_controller = PluginController(user_profile=user_profile, manifest=manifest)
        plugin = plugin_controller.plugin
        if not plugin or plugin.plugin_meta is None:
            raise SmarterValueError("ChatBotPlugin.load() failed to load plugin from data file")
        return cls.objects.create(chatbot=chatbot, plugin_meta=plugin.plugin_meta)

    @classmethod
    def plugins(cls, chatbot: ChatBot) -> List[PluginBase]:
        """
        Returns a list of Plugin instances associated with the given ChatBot.

        :param chatbot: The ChatBot instance to retrieve plugins for.
        :returns: List of Plugin instances.
        :rtype: List[PluginBase]

        :raises SmarterValueError: If admin user for chatbot account is not found
                                   or if a plugin fails to load.

        See Also:

        - :py:class:`smarter.apps.plugin.controller.PluginController`
        """
        if not chatbot:
            return []
        chatbot_plugins = cls.objects.filter(chatbot=chatbot)
        admin_user = UserProfile.admin_for_account(chatbot.user_profile.cached_account)
        if admin_user is None:
            raise SmarterValueError("ChatBotPlugin.plugin() failed to find admin user for chatbot account")
        user_profile = UserProfile.get_cached_object(invalidate=False, user=admin_user)
        retval = []
        for chatbot_plugin in chatbot_plugins:
            plugin_controller = PluginController(
                user_profile=user_profile,
                plugin_meta=chatbot_plugin.plugin_meta,
            )
            if not plugin_controller or not plugin_controller.plugin:
                raise SmarterValueError(
                    f"ChatBotPlugin.plugins() failed to load plugin for {chatbot_plugin.plugin_meta.name}"
                )
            retval.append(plugin_controller.plugin)
        return retval

    # pylint: disable=W0221
    @classmethod
    def get_cached_objects(
        cls, invalidate: Optional[bool] = False, chatbot: Optional[ChatBot] = None
    ) -> models.QuerySet["ChatBotPlugin"]:
        """
        Retrieve a queryset of ChatBotPlugin instances associated with a ChatBot using caching.

        :param invalidate: Whether to invalidate the cache for this retrieval.
        :type invalidate: bool, optional
        :param chatbot: The ChatBot instance for which to retrieve plugins.
        :type chatbot: ChatBot, optional

        :returns: A queryset of ChatBotPlugin instances associated with the ChatBot.
        :rtype: models.QuerySet["ChatBotPlugin"]

        """
        logger_prefix = formatted_text(__name__ + "." + ChatBotPlugin.__name__ + ".get_cached_objects()")
        logger.debug("%s called with chatbot=%s, invalidate=%s", logger_prefix, chatbot, invalidate)

        @cache_results()
        def _get_plugins_for_chatbot_id(
            chatbot_id: int, class_name: str = cls.__name__
        ) -> models.QuerySet["ChatBotPlugin"]:
            """
            Caches the plugins for a chatbot by chatbot_id to optimize
            performance and reduce database queries.

            :param chatbot_id: The ID of the ChatBot for which to retrieve plugins.
            :param class_name: The name of the class for cache key purposes.
            :returns: A queryset of ChatBotPlugin instances associated with the ChatBot.
            :rtype: models.QuerySet["ChatBotPlugin"]
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
            _get_plugins_for_chatbot_id.invalidate(chatbot_id=chatbot.id, class_name=cls.__name__)  # type: ignore[union-attr]

        if chatbot:
            return _get_plugins_for_chatbot_id(chatbot_id=chatbot.id, class_name=cls.__name__)  # type: ignore[return-value]

        return super().get_cached_objects(invalidate=invalidate)  # type: ignore[return-value]

    @classmethod
    def plugins_json(cls, chatbot: ChatBot) -> List[dict]:
        retval = []
        for plugin in cls.plugins(chatbot):
            retval.append(plugin.to_json())
        return retval


__all__ = [
    "ChatBotPlugin",
]
