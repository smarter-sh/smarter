# pylint: disable=W0613
"""
Smarter API command-line interface Brokers. These are the broker classes
that implement the broker service pattern for an underlying object. Brokers
receive a Yaml manifest representation of a model, convert this to a Pydantic
model, and then instantiate the appropriate Python class that perform
the necessary operations to facilitate get, post, put, and delete operations.
"""

from typing import Dict, Type

from smarter.apps.chatbot.manifest.brokers.chatbot import SAMChatbotBroker
from smarter.apps.plugin.manifest.brokers.plugin import SAMPluginBroker
from smarter.apps.plugin.manifest.brokers.sql_connection import (
    SAMPluginDataSqlConnectionBroker,
)
from smarter.lib.drf.manifest.brokers.auth_token import SAMSmarterAuthTokenBroker
from smarter.lib.manifest.broker import AbstractBroker, BrokerNotImplemented

from ..manifests.enum import SAMKinds


BROKERS: Dict[str, Type[AbstractBroker]] = {
    SAMKinds.ACCOUNT.value: BrokerNotImplemented,
    SAMKinds.APIKEY.value: SAMSmarterAuthTokenBroker,
    SAMKinds.CHAT.value: BrokerNotImplemented,
    SAMKinds.CHATBOT.value: SAMChatbotBroker,
    SAMKinds.PLUGIN.value: SAMPluginBroker,
    SAMKinds.SQLCONNECTION.value: SAMPluginDataSqlConnectionBroker,
    SAMKinds.USER.value: BrokerNotImplemented,
}
