# pylint: disable=W0613
"""
Smarter API command-line interface Brokers. These are the broker classes
that implement the broker service pattern for an underlying object. Brokers
receive a Yaml manifest representation of a model, convert this to a Pydantic
model, and then instantiate the appropriate Python class that perform
the necessary operations to facilitate get, post, put, and delete operations.
"""

from typing import Dict, Type

from smarter.apps.api.v1.manifests.broker import AbstractBroker
from smarter.apps.api.v1.manifests.enum import SAMKinds
from smarter.apps.plugin.api.v1.manifests.broker import SAMPluginBroker


BROKERS: Dict[str, Type[AbstractBroker]] = {
    SAMKinds.PLUGIN.value: SAMPluginBroker,
    SAMKinds.ACCOUNT.value: None,
    SAMKinds.USER.value: None,
    SAMKinds.CHAT.value: None,
    SAMKinds.CHATBOT.value: None,
}
