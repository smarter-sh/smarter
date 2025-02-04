# pylint: disable=W0613
"""
Smarter API command-line interface Brokers. These are the broker classes
that implement the broker service pattern for an underlying object. Brokers
receive a Yaml manifest representation of a model, convert this to a Pydantic
model, and then instantiate the appropriate Python class that performs
the necessary operations to facilitate cli requests that include:
    - delete
    - deploy
    - describe
    - get
    - logs
    - manifest
    - undeploy
"""

import logging
from typing import Dict, Type
from urllib.parse import urlparse

from smarter.apps.account.manifest.brokers.account import SAMAccountBroker
from smarter.apps.account.manifest.brokers.user import SAMUserBroker
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.chat.manifest.brokers.chat import SAMChatBroker
from smarter.apps.chat.manifest.brokers.chat_history import SAMChatHistoryBroker
from smarter.apps.chat.manifest.brokers.chat_plugin_usage import (
    SAMChatPluginUsageBroker,
)
from smarter.apps.chat.manifest.brokers.chat_tool_call import SAMChatToolCallBroker
from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker
from smarter.apps.plugin.manifest.brokers.plugin import SAMPluginBroker
from smarter.apps.plugin.manifest.brokers.sql_connection import (
    SAMPluginDataSqlConnectionBroker,
)
from smarter.common.exceptions import SmarterConfigurationError
from smarter.lib.drf.manifest.brokers.auth_token import SAMSmarterAuthTokenBroker
from smarter.lib.manifest.broker import AbstractBroker, BrokerNotImplemented


logger = logging.getLogger(__name__)


class Brokers:
    """Broker service pattern for an underlying object. Maps SAMKinds to Broker classes."""

    _brokers: Dict[str, Type[AbstractBroker]] = {
        SAMKinds.ACCOUNT.value: SAMAccountBroker,
        SAMKinds.APIKEY.value: SAMSmarterAuthTokenBroker,
        SAMKinds.CHAT.value: SAMChatBroker,
        SAMKinds.CHAT_HISTORY.value: SAMChatHistoryBroker,
        SAMKinds.CHAT_PLUGIN_USAGE.value: SAMChatPluginUsageBroker,
        SAMKinds.CHAT_TOOL_CALL.value: SAMChatToolCallBroker,
        SAMKinds.CHATBOT.value: SAMChatbotBroker,
        SAMKinds.PLUGIN.value: SAMPluginBroker,
        SAMKinds.SQLCONNECTION.value: SAMPluginDataSqlConnectionBroker,
        SAMKinds.APICONNECTION.value: BrokerNotImplemented,
        SAMKinds.USER.value: SAMUserBroker,
    }

    @classmethod
    def _lower_brokers(cls):
        return {k.lower(): v for k, v in cls._brokers.items()}

    @classmethod
    def get_broker(cls, kind: str) -> Type[AbstractBroker]:
        """Case insensitive broker getter."""
        return cls._brokers.get(kind) or cls._lower_brokers().get(kind.lower())

    @classmethod
    def snake_to_camel(cls, snake_str):
        components = snake_str.split("_")
        return components[0] + "".join(x.title() for x in components[1:])

    @classmethod
    def get_broker_kind(cls, kind: str) -> str:
        """
        Case insensitive broker kind getter. Returns the original SAMKinds
        key string from cls._brokers for the given kind.
        """
        if not kind:
            return None

        # remove trailing 's' from kind if it exists
        if kind.endswith("s"):
            kind = kind[:-1]

        # ensure kind is in camel case
        kind = cls.snake_to_camel(kind)
        lower_kind = kind.lower()

        # perform a lower case search to find and return the original key
        # in the cls._brokers dictionary
        for key in cls._brokers:
            if key.lower() == lower_kind:
                return key
        return None

    @classmethod
    def all_brokers(cls) -> list[str]:
        return list(cls._brokers.keys())

    @classmethod
    def from_url(cls, url) -> str:
        """
        Returns the kind of broker from the given URL. This is used to
        determine the broker to use when the kind is not provided in the
        request.

        example: http://localhost:8000/api/v1/cli/example_manifest/Account/
        """
        parsed_url = urlparse(url)
        if parsed_url:
            slugs = parsed_url.path.split("/")
            if not "api" in slugs:
                return None
            for slug in slugs:
                this_slug = str(slug).lower()
                kind = cls.get_broker_kind(this_slug)
                if kind:
                    return kind
        logger.warning("Brokers.from_url() could not extract manifest kind from URL: %s", url)


# an internal self-check to ensure that all SAMKinds have a Broker implementation
if not all(item in SAMKinds.all_values() for item in Brokers.all_brokers()):
    brokers_keys = set(Brokers.all_brokers())
    samkinds_values = set(SAMKinds.all_values())
    difference = brokers_keys.difference(samkinds_values)
    difference_list = list(difference)
    if len(difference_list) == 1:
        difference_list = difference_list[0]
    raise SmarterConfigurationError(
        f"The following broker(s) is missing from the master BROKERS dictionary: {difference_list}"
    )
