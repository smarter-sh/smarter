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

from typing import Dict, Type

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


BROKERS: Dict[str, Type[AbstractBroker]] = {
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

# an internal self-check to ensure that all SAMKinds have a Broker implementation
if not all(item in SAMKinds.all_values() for item in BROKERS):
    brokers_keys = set(BROKERS.keys())
    samkinds_values = set(SAMKinds.all_values())
    difference = brokers_keys.difference(samkinds_values)
    difference_list = list(difference)
    if len(difference_list) == 1:
        difference_list = difference_list[0]
    raise SmarterConfigurationError(
        f"The following broker(s) is missing from the master BROKERS dictionary: {difference_list}"
    )
