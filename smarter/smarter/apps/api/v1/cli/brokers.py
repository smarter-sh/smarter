# pylint: disable=W0613
"""
Smarter API command-line interface Brokers. These are the broker classes
that implement the broker service pattern for an underlying object. Brokers
receive a Yaml manifest representation of a model, convert this to a Pydantic
model, and then instantiate the appropriate Python class that perform
the necessary operations to facilitate get, post, put, and delete operations.
"""

from typing import Dict, Type

from smarter.apps.plugin.manifest.broker import SAMPluginBroker
from smarter.lib.manifest.broker import AbstractBroker, BrokerNotImplemented

from ..manifests.enum import SAMKinds


BROKERS: Dict[str, Type[AbstractBroker]] = {
    SAMKinds.PLUGIN.value: SAMPluginBroker,
    SAMKinds.ACCOUNT.value: BrokerNotImplemented,
    SAMKinds.USER.value: BrokerNotImplemented,
    SAMKinds.CHAT.value: BrokerNotImplemented,
    SAMKinds.CHATBOT.value: BrokerNotImplemented,
}
